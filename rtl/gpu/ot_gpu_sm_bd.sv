`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// V4.1 block-dot SM element of the GPU-organised HBM comparator: SUB
// sub-partitions of LBS block-dot lanes each (8 per SM: 256 FP4 weights =
// 128 B a cycle, the SM's ingest), NC columns, the x store of E4M3 activation
// blocks, the cross-sub-partition tree and one streaming stack per column.
//
// Exactness (tools/hdc_golden_v41.py linear_q under R-ARITH chunk8): K is
// cut into 32-wide blocks; a block term is the exact dot of the E4M3/E2M1
// codes, rounded once to FP32 and scaled by 2^(e_w + e_x); csum adds chunks of
// 8 consecutive terms sequentially from +0, then a pairwise tree over the
// chunk sums padded with +0.  Lane j of the SM holds chunk (g * LA + j),
// LA = the op's active lanes (8 for FP4; 4 for FP8, whose 32-byte blocks
// halve the lanes one 128-byte line feeds -- lanes past LA carry +0, the
// golden pad), so the lane trees are csum's bottom levels and the stack
// continues it over the groups.  The row's whole K stays in this SM.
// Output: the FP32 accumulator (linear_q rounds it to BF16 after an optional
// folded scale; the rounding is the consumer's).
// ---------------------------------------------------------------------------
module ot_gpu_sm_bd #(
    parameter integer SUB    = 4,
    parameter integer LBS    = 2,
    parameter integer NC     = 2,
    parameter integer IL     = 8,
    parameter integer XDEPTH = 64,
    parameter integer RMAX   = 4096,
    parameter integer LEV    = 3
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,        // blocks per chunk (8; fewer in a short tail op)
    input  wire [7:0]              op_g,
    input  wire                    op_gs,       // group-slot issue (ot_gpu_issue)
    input  wire                    op_fp4,
    output wire                    busy,
    input  wire                    w_valid,
    output wire                    w_ready,
    input  wire [SUB*LBS*266-1:0]  w_data,      // [lane] {we[9:0], wq[255:0]}
    input  wire                    xw_en,
    input  wire [$clog2(XDEPTH)-1:0] xw_addr,
    input  wire [SUB*LBS*NC*266-1:0] xw_data,   // [col][lane] {xe[9:0], xq[255:0]}
    output reg                     rv,
    output reg  [$clog2(RMAX)-1:0] rrow,
    output reg  [NC*32-1:0]        rdata,
    output reg                     fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    localparam integer LB  = SUB * LBS;
    localparam integer SW  = $clog2(IL);
    localparam integer RW  = $clog2(RMAX);
    localparam integer XW  = $clog2(XDEPTH);
    localparam integer TAGW = RW + 1 + SW;
    reg         fp4_q;
    wire        sv;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fp4_q <= 1'b0;
        else if (start && !busy) fp4_q <= op_fp4;
    ot_gpu_issue #(.IL(IL), .RMAX(RMAX), .XDEPTH(XDEPTH)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(busy), .iss_v(adv), .iss_row_ok(row_ok),
        .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last), .iss_glast(i_glast), .iss_rev_end(),
        .xa(xa), .arrive(arrive), .release_in(release_in), .released(released));
    reg [LB*NC*266-1:0] xmem [0:XDEPTH-1];
    always @(posedge clk) if (xw_en) xmem[xw_addr] <= xw_data;
    reg              iv, ifirst, ilast;
    reg [TAGW-1:0]   itag;
    reg [LB*266-1:0] iw;
    reg [LB*NC*266-1:0] ix;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv <= 1'b0; ifirst <= 1'b0; ilast <= 1'b0; end
        else begin iv <= adv && row_ok; ifirst <= i_first; ilast <= i_last; end
    end
    always @(posedge clk) begin
        itag <= {row_now[RW-1:0], i_glast, si};
        ix <= xmem[xa];
        iw <= w_data;
    end
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*RW-1:0] crow;
    genvar col, sp, q;
    generate for (col = 0; col < NC; col = col + 1) begin : g_col
        wire [SUB-1:0] sov, sfault;
        wire [SUB*32-1:0] sy;
        wire [SUB*TAGW-1:0] stag;
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
            wire [LBS*256-1:0] wq_s, xq_s;
            wire [LBS*10-1:0]  we_s, xe_s;
            for (q = 0; q < LBS; q = q + 1) begin : g_l
                assign wq_s[256*q +: 256] = iw[(sp*LBS + q)*266 +: 256];
                assign we_s[10*q +: 10]   = iw[(sp*LBS + q)*266 + 256 +: 10];
                assign xq_s[256*q +: 256] = ix[(col*LB + sp*LBS + q)*266 +: 256];
                assign xe_s[10*q +: 10]   = ix[(col*LB + sp*LBS + q)*266 + 256 +: 10];
            end
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv), .first(ifirst), .last(ilast), .fp4(fp4_q), .tag(itag),
                .wq(wq_s), .we(we_s), .xq(xq_s), .xe(xe_s),
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
    assign sv = cv[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; fault <= 1'b0; end
        else begin rv <= cv[0]; fault <= fault | (|cf); end
    end
    always @(posedge clk) begin rrow <= crow[RW-1:0]; rdata <= cy; end
endmodule
