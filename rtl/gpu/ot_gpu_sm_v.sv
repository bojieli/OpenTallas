`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The hardened SM element of the DeepSeek-V4.1 HBM comparator (the macro the
// V4.1 die floorplan replicates 32 times; tools/uarch_model.hbm_gpu_design("v41")).
// Same arithmetic and schedule as ot_gpu_sm_bd / ot_gpu_sm (the bit-exact
// functional models), built from its physical parts:
//   * the bulk-copy engine with its staging ring in hard SRAM macros; a line
//     is 128 B of weights + 8 block exponents (E8M0): 8 FP4 blocks (16 B
//     packed each), 4 FP8 blocks (32 B each), or 64 BF16 weights;
//   * the weight unpack (FP4 nibbles -> the block-dot lane's byte codes);
//   * the x store: XM shallow hard SRAM macros read EVERY cycle, one whole
//     fragment (every lane's x for every column at one (group, k-step)) a
//     read, so group-slot issue (a row's groups on different slots) runs at
//     one item a cycle -- the V4.1 1/96 row slices are 1-2 rows an SM;
//   * SUB x NC block-dot columns (ot_gpu_bd_col, 2 lanes each) and SUB x NC
//     BF16 columns (ot_gpu_tc_col, 16 lanes each), their combine trees, one
//     streaming stack per column, FP32 results (the consumer rounds);
//   * the issue sequencer (row-slot or group-slot) and the barrier handshake.
// op_fmt: 0 BF16 (chunk 8 products, 64 lanes), 1 FP8 (4 active block-dot
// lanes), 2 FP4 (8 block-dot lanes).
// ---------------------------------------------------------------------------
module ot_gpu_sm_v #(
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer XD   = 128,        // x store depth (fragments)
    parameter integer MAX_OUT = 512
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    output wire                    busy,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [NC*(SUB*LBS*266+SUB*LSB*16)-1:0] xw_data,
    output reg                     rv,
    output reg  [$clog2(RMAX)-1:0] rrow,
    output reg  [NC*32-1:0]        rdata,
    output reg                     fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    localparam integer LB   = SUB * LBS;            // block-dot lanes
    localparam integer LF   = SUB * LSB;            // BF16 lanes
    localparam integer XC   = LB * 266 + LF * 16;   // x bits per column
    localparam integer FRAGW = NC * XC;
    localparam integer XM   = (FRAGW + 255) / 256;
    localparam integer SW   = $clog2(IL);
    localparam integer RW   = $clog2(RMAX);
    localparam integer XW   = $clog2(XD);
    localparam integer TAGW = RW + 1 + SW;

    // ---------------- bulk copy ----------------
    wire          w_valid, w_ready;
    wire [1087:0] w_data;
    ot_gpu_bulk_copy #(.LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
        .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
        .s_valid(w_valid), .s_ready(w_ready), .s_data(w_data), .outstanding(), .idle());

    // ---------------- issue ----------------
    reg  [1:0]  fmt_q;
    wire        sv;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fmt_q <= 2'd0;
        else if (start && !busy) fmt_q <= op_fmt;
    ot_gpu_issue #(.IL(IL), .RMAX(RMAX), .XDEPTH(XD)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(arrive), .release_in(release_in),
        .released(released));

    // ---------------- x store: XM macros, one fragment a read ----------------
    wire [XM*256-1:0] xrd;
    wire [XM*256-1:0] xwd = {{(XM*256-FRAGW){1'b0}}, xw_data};
    genvar m;
    generate for (m = 0; m < XM; m = m + 1) begin : g_xm
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(adv && row_ok), .r_addr_in(xa), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(xw_en), .w_addr_in(xw_addr), .wd_in(xwd[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate

    // ---------------- stage 1: line and tag (the x read is in flight) ----------------
    reg              s1_v, s1_first, s1_last;
    reg [TAGW-1:0]   s1_tag;
    reg [1087:0]     s1_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_first <= 1'b0; s1_last <= 1'b0; end
        else begin s1_v <= adv && row_ok; s1_first <= i_first; s1_last <= i_last; end
    end
    always @(posedge clk) begin
        s1_tag <= {row_now[RW-1:0], i_glast, si};
        s1_w <= w_data;
    end
    // ---------------- stage 2: unpack, x fragment ----------------
    reg              iv_b, iv_f, ifirst, ilast;
    reg [TAGW-1:0]   itag;
    reg [LB*256-1:0] iwq;
    reg [LB*10-1:0]  iwe;
    reg [LF*16-1:0]  iwf;
    reg [FRAGW-1:0]  ix;
    reg              ifp4;
    integer j, b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv_b <= 1'b0; iv_f <= 1'b0; ifirst <= 1'b0; ilast <= 1'b0; end
        else begin
            iv_b <= s1_v && (fmt_q != 2'd0);
            iv_f <= s1_v && (fmt_q == 2'd0);
            ifirst <= s1_first; ilast <= s1_last;
        end
    end
    always @(posedge clk) begin
        itag <= s1_tag;
        ix <= xrd[FRAGW-1:0];
        ifp4 <= (fmt_q == 2'd2);
        iwf <= s1_w[LF*16-1:0];
        for (j = 0; j < LB; j = j + 1) begin
            iwe[10*j +: 10] <= {2'b00, s1_w[1024 + 8*j +: 8]} - 10'sd127;
            for (b = 0; b < 32; b = b + 1)
                if (fmt_q == 2'd2)       // FP4: lane j's block is 16 packed bytes, E2M1 in the low nibble
                    iwq[256*j + 8*b +: 8] <= {4'd0, s1_w[128*j + 4*b +: 4]};
                else                      // FP8: 4 lanes of 32 E4M3 bytes; lanes past 4 carry +0
                    iwq[256*j + 8*b +: 8] <= (j < LB / 2) ? s1_w[256*j + 8*b +: 8] : 8'd0;
        end
    end

    // ---------------- columns ----------------
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*RW-1:0] crow;
    genvar col, sp, q;
    generate for (col = 0; col < NC; col = col + 1) begin : g_col
        wire [SUB-1:0] bov, bfault, fov, ffault;
        wire [SUB*32-1:0] by, fy;
        wire [SUB*TAGW-1:0] btag, ftag;
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
            wire [LBS*256-1:0] xq_s;
            wire [LBS*10-1:0]  xe_s;
            wire [LSB*16-1:0]  xf_s;
            for (q = 0; q < LBS; q = q + 1) begin : g_b
                assign xq_s[256*q +: 256] = ix[col*XC + (sp*LBS + q)*266 +: 256];
                assign xe_s[10*q +: 10]   = ix[col*XC + (sp*LBS + q)*266 + 256 +: 10];
            end
            for (q = 0; q < LSB; q = q + 1) begin : g_f
                assign xf_s[16*q +: 16] = ix[col*XC + LB*266 + (sp*LSB + q)*16 +: 16];
            end
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iwq[sp*LBS*256 +: LBS*256]), .we(iwe[sp*LBS*10 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov[sp]), .y(by[32*sp +: 32]), .otag(btag[TAGW*sp +: TAGW]), .fault(bfault[sp]));
            if (LSB == 16 && TAGW == 16 && IL == 8) begin : g_hard
                // the hardened 16-lane macro (full-shape SM: 4,096 rows, 8 slots)
                ot_gpu_tc16 u_tc (
                    .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                    .w(iwf[sp*LSB*16 +: LSB*16]), .x(xf_s),
                    .ov(fov[sp]), .y(fy[32*sp +: 32]), .otag(ftag[TAGW*sp +: TAGW]), .fault(ffault[sp]));
            end else begin : g_soft
                ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                    .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                    .w(iwf[sp*LSB*16 +: LSB*16]), .x(xf_s),
                    .ov(fov[sp]), .y(fy[32*sp +: 32]), .otag(ftag[TAGW*sp +: TAGW]), .fault(ffault[sp]));
            end
        end
        // the two column types never run in one op: one combine tree takes whichever retires
        wire          tin_v = bov[0] | fov[0];
        wire [SUB*32-1:0] tin = bov[0] ? by : fy;
        wire [TAGW-1:0] tin_tag = bov[0] ? btag[TAGW-1:0] : ftag[TAGW-1:0];
        wire tv, tf;
        wire [31:0] ty;
        wire [TAGW-1:0] tt;
        ot_gpu_tree #(.N(SUB), .TAGW(TAGW)) u_comb (.clk(clk), .rst_n(rst_n), .v(tin_v), .d(tin),
                                                  .tag(tin_tag), .ov(tv), .y(ty), .otag(tt), .fault(tf));
        wire kf;
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(cv[col]), .y(cy[32*col +: 32]), .otag(crow[RW*col +: RW]), .fault(kf));
        assign cf[col] = (|bfault) | (|ffault) | tf | kf | (bov[0] & fov[0]);
    end endgenerate
    assign sv = cv[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; fault <= 1'b0; end
        else begin rv <= cv[0]; fault <= fault | (|cf); end
    end
    always @(posedge clk) begin rrow <= crow[RW-1:0]; rdata <= cy; end
endmodule
