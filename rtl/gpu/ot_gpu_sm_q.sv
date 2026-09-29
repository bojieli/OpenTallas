`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The hardened SM element of the Qwen3-8B HBM comparator (the macro the die
// floorplan replicates 32 times; docs/MICROARCH_MODEL.md, tools/uarch_model.py
// hbm_gpu_design("qwen")).  Same arithmetic and schedule as ot_gpu_sm (the
// bit-exact functional model), built from its physical parts:
//   * the TMA-style bulk-copy engine with its staging ring in 4 hard SRAM
//     macros (128 KB, one 128-B line a cycle to the tensor core);
//   * the x store: 16 hard SRAM macros and a double-buffered fragment register;
//   * SUB x NC tensor-core columns (ot_gpu_tc_col, the hardened MMA macro),
//     the INT8 -> BF16 weight decode shared by a sub-partition's columns;
//   * per column the SUB-leaf combine tree, the streaming stack and the
//     FP32 x BF16 row-scale multiply; the row scales in one SRAM macro;
//   * the row-slot issue sequencer and the barrier arrive / release.
// Pipeline: issue (stage 1: line, tag, fragment name) -> stage 2 (decode, x
// fragment read) -> columns.
// ---------------------------------------------------------------------------
module ot_gpu_sm_q #(
    parameter integer SUB  = 4,
    parameter integer LS   = 32,
    parameter integer NC   = 16,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 5,
    parameter integer NXM  = 16,        // x-store macros
    parameter integer MAX_OUT = 512
) (
    input  wire                    clk,
    input  wire                    rst_n,
    // op
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_scale,
    output wire                    busy,
    // bulk copy: descriptors, reads to the NoC / HBM controller, responses in any order
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
    input  wire [SUB*LS*8-1:0]     rsp_data,
    // x store and row-scale store writes (from the x broadcast / L2)
    input  wire                    xw_en,
    input  wire [9:0]              xw_addr,
    input  wire [NXM*256-1:0]      xw_data,
    input  wire                    sw_en,
    input  wire [$clog2(RMAX)-1:0] sw_addr,
    input  wire [15:0]             sw_data,
    // results
    output reg                     rv,
    output reg  [$clog2(RMAX)-1:0] rrow,
    output reg  [NC*32-1:0]        rdata,
    output reg                     fault,
    // barrier network
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    localparam integer L    = SUB * LS;
    localparam integer SW   = $clog2(IL);
    localparam integer RW   = $clog2(RMAX);
    localparam integer FRAGW = L * NC * 16;
    localparam integer TAGW = RW + 1 + SW;
    localparam integer XDEPTH = 1024;

    // ---------------- bulk copy ----------------
    wire             w_valid, w_ready;
    wire [L*8-1:0]   w_data;
    wire [$clog2(MAX_OUT+1)-1:0] outstanding;
    ot_gpu_bulk_copy #(.LINE_BITS(L * 8), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
        .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
        .s_valid(w_valid), .s_ready(w_ready), .s_data(w_data), .outstanding(outstanding), .idle());

    // ---------------- op state, x store, issue ----------------
    reg         scale_q;
    wire        sv;
    wire        adv, row_ok, i_first, i_last, i_glast, rev_end, x_rdy, head_sel;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [FRAGW-1:0] frag;
    reg         s1_rsel;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) scale_q <= 1'b0;
        else if (start && !busy) scale_q <= op_scale;
    ot_gpu_issue #(.IL(IL), .RMAX(RMAX), .XDEPTH(XDEPTH)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(1'b0),
        .w_valid(w_valid), .x_rdy(x_rdy), .w_ready(w_ready), .rdone(sv), .busy(busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(rev_end), .xa(), .arrive(arrive), .release_in(release_in),
        .released(released));
    ot_gpu_xstore #(.NM(NXM), .FRAGW(FRAGW)) u_x (
        .clk(clk), .rst_n(rst_n), .start(start && !busy), .op_nfrag(op_c * op_g),
        .op_blocks((op_rows + IL - 1) / IL), .pop(rev_end), .ready(x_rdy), .head_sel(head_sel),
        .rsel(s1_rsel), .frag(frag), .w_en(xw_en), .w_addr(xw_addr), .w_data(xw_data));

    // ---------------- stage 1: the line, the tag and the fragment's buffer ----------------
    function automatic [15:0] i8_bf16(input [7:0] code);
        reg s; reg [7:0] m; reg [2:0] msb; reg [7:0] nrm; integer b;
        begin
            s = code[7];
            m = s ? (~code + 8'd1) : code;
            msb = 3'd0;
            for (b = 0; b < 8; b = b + 1) if (m[b]) msb = b[2:0];
            nrm = m << (3'd7 - msb);
            i8_bf16 = (m == 8'd0) ? 16'd0 : {s, 8'd127 + {5'd0, msb}, nrm[6:0]};
        end
    endfunction
    reg              s1_v, s1_first, s1_last;
    reg [TAGW-1:0]   s1_tag;
    reg [L*8-1:0]    s1_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_first <= 1'b0; s1_last <= 1'b0; end
        else begin s1_v <= adv && row_ok; s1_first <= i_first; s1_last <= i_last; end
    end
    always @(posedge clk) begin
        s1_tag <= {row_now[RW-1:0], i_glast, si};
        s1_w <= w_data;
        s1_rsel <= head_sel;
    end
    // ---------------- stage 2: decode, x fragment ----------------
    reg              iv, ifirst, ilast;
    reg [TAGW-1:0]   itag;
    reg [L*16-1:0]   iw;
    reg [FRAGW-1:0]  ix;
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv <= 1'b0; ifirst <= 1'b0; ilast <= 1'b0; end
        else begin iv <= s1_v; ifirst <= s1_first; ilast <= s1_last; end
    end
    always @(posedge clk) begin
        itag <= s1_tag;
        ix <= frag;
        for (j = 0; j < L; j = j + 1) iw[16*j +: 16] <= i8_bf16(s1_w[8*j +: 8]);
    end

    // ---------------- columns ----------------
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*RW-1:0] crow;
    genvar col, sp, q;
    generate for (col = 0; col < NC; col = col + 1) begin : g_col
        wire [SUB-1:0] sov, sfault;
        wire [SUB*32-1:0] sy;
        wire [SUB*TAGW-1:0] stag;
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
            wire [LS*16-1:0] xs;
            for (q = 0; q < LS; q = q + 1) begin : g_x
                assign xs[16*q +: 16] = ix[(col * L + sp * LS + q) * 16 +: 16];
            end
            ot_gpu_tc_col #(.L(LS), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[sp*LS*16 +: LS*16]), .x(xs),
                .ov(sov[sp]), .y(sy[32*sp +: 32]), .otag(stag[TAGW*sp +: TAGW]), .fault(sfault[sp]));
        end
        wire tv, tf;
        wire [31:0] ty;
        wire [TAGW-1:0] tt;
        ot_gpu_tree #(.N(SUB), .TAGW(TAGW)) u_comb (.clk(clk), .rst_n(rst_n), .v(sov[0]), .d(sy),
                                                  .tag(stag[TAGW-1:0]), .ov(tv), .y(ty), .otag(tt), .fault(tf));
        wire kf;
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(cv[col]), .y(cy[32*col +: 32]), .otag(crow[RW*col +: RW]), .fault(kf));
        assign cf[col] = (|sfault) | tf | kf;
    end endgenerate

    // ---------------- row scale: one SRAM macro of 16 BF16 scales a word ----------------
    wire [RW-1:0] krow0 = crow[RW-1:0];
    wire [255:0]  srd;
    ot_sram_1r1w_256x256_m2_r2c2 u_scale (
        .clk(clk), .r_ce_in(cv[0]), .r_addr_in(krow0[RW-1:4]), .rd_out(srd),
        .w_ce_in(sw_en), .w_addr_in(sw_addr[RW-1:4]), .wd_in({16{sw_data}}),
        .w_mask_in({240'd0, 16'hFFFF} << (16 * sw_addr[3:0])),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg  [NC*32-1:0] ky_q;
    reg  kv_q;
    reg  [RW-1:0] krow_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kv_q <= 1'b0;
        else kv_q <= cv[0];
    always @(posedge clk) begin
        ky_q <= cy;
        krow_q <= krow0;
    end
    wire [15:0] ksc = srd[16 * krow_q[3:0] +: 16];
    wire [NC*32-1:0] sy_out;
    wire [NC-1:0] mf;
    generate for (col = 0; col < NC; col = col + 1) begin : g_scale
        ot_hdc_fmul u_mul (.clk(clk), .rst_n(rst_n), .v(kv_q && scale_q), .a(ky_q[32*col +: 32]),
                           .b({ksc, 16'd0}), .y(sy_out[32*col +: 32]), .fault(mf[col]));
    end endgenerate
    wire [5:0] svl;
    ot_hdc_vline #(.D(5)) u_sv (.clk(clk), .rst_n(rst_n), .v(kv_q), .vd(svl));
    wire [RW-1:0] srow;
    ot_hdc_delay #(.W(RW), .D(5)) u_sr (.clk(clk), .rst_n(rst_n), .d(krow_q), .q(srow));
    wire [NC*32-1:0] ky_d;
    ot_hdc_delay #(.W(NC*32), .D(5)) u_sy (.clk(clk), .rst_n(rst_n), .d(ky_q), .q(ky_d));
    assign sv = svl[5];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; fault <= 1'b0; end
        else begin
            rv <= sv;
            fault <= fault | (|cf) | (|mf);
        end
    end
    always @(posedge clk) begin
        rrow <= srow;
        rdata <= scale_q ? sy_out : ky_d;
    end
endmodule
