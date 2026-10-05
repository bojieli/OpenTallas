`timescale 1ns/1ps
// Pauli opt3 leaf for Euclid production SM: x_addr and b_addr are final absolute ring addresses.
// XMAP changes only constant bit positions. No xb input/addition or issue/control state.
module ot_hbm_accel_smpq_xmap_leaf #(
    parameter integer SUB = 4,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 8,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer COL = 0,
    parameter integer SP  = 0,
    parameter integer TCK = 1,
    parameter integer XMAP = 0,        // Opt3 default-off static format-masked activation map
    parameter integer G1ASB = 0
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [6+TAGW-1:0]        c_in,
    input  wire [LBS*266+LSB*16-1:0] w_in,
    input  wire                     x_ce,
    input  wire [$clog2(XD)-1:0]    x_addr,
    input  wire                     b_en,
    input  wire [$clog2(XD)-1:0]    b_addr,
    input  wire [NBEAT-1:0]         b_oh,
    input  wire [2047:0]            b_data,
    output reg                      gv,
    output reg  [31:0]              gy,
    output reg  [TAGW-1:0]          gt,
    output reg                      gf
);
    // The released writer's 3152-bit fragment is the selected SUB4/LBS2/LSB16 shape.
    generate if (XMAP && (SUB != 4 || LBS != 2 || LSB != 16)) begin : g_bad_xmap_shape
        initial $fatal(1, "Unsupported activation XMAP shape");
    end endgenerate
    localparam integer LB  = SUB * LBS;
    localparam integer XC  = LB * 266 + SUB * LSB * 16;
    localparam integer SLW = LBS * 266 + LSB * 16;
    localparam integer WSW = SLW;
    localparam integer NXL = (SLW + 255) / 256;
    localparam integer XW  = $clog2(XD);
    localparam integer CW  = 6 + TAGW;
    // ---- E3: line and control ----
    reg  [1:0]     c3v;                 // iv_b, iv_f
    reg  [CW-3:0]  c3d;                 // first, last, fp4, bf16-op, tag
    reg  [WSW-1:0] w3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c3v <= 2'b00;
        else c3v <= c_in[CW-1:CW-2];
    always @(posedge clk) begin c3d <= c_in[CW-3:0]; w3 <= w_in; end
    // ---- x write: the beat's bits of this slice, per-bit masks from the one-hot beat group ----
    reg               we_q;
    reg [XW-1:0]      wa_q;
    reg [NBEAT-1:0]   woh_q;
    reg [SLW-1:0]     wd_q;
    wire [SLW-1:0]    wd_n;
    wire [NXL*256-1:0] wd_m, wm_m;
    genvar b, m, qq;
    generate for (b = 0; b < SLW; b = b + 1) begin : g_wb
        // fragment bit of slice bit b (ot_gpu_sm_v layout)
        localparam integer J = SP * LBS + b / 266;
        // Constant elaboration wiring only: no run-time format selector.
        localparam integer F_OLD = (b < LBS * 266) ? COL * XC + J * 266 + (b % 266)
                                                    : COL * XC + LB * 266 + SP * LSB * 16 + (b - LBS * 266);
        localparam integer F_MASKED = (b < LBS * 266) ? (J / 4) * NC * 1064 + COL * 1064 + (J % 4) * 266 + b % 266
                                                    : COL * (SUB * LSB * 16) + SP * LSB * 16 + (b - LBS * 266);
        localparam integer F = XMAP ? F_MASKED : F_OLD;
        assign wd_n[b] = b_data[F % 2048];
        assign wd_m[b] = wd_q[b];
        assign wm_m[b] = woh_q[F / 2048];
    end
    for (b = SLW; b < NXL * 256; b = b + 1) begin : g_pad
        assign wd_m[b] = 1'b0;
        assign wm_m[b] = 1'b0;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) we_q <= 1'b0;
        else we_q <= b_en;
    always @(posedge clk) begin wa_q <= b_addr; woh_q <= b_oh; wd_q <= wd_n; end
    // ---- x store: NXL macros, read from the L2 address (latched at E3) ----
    wire [NXL*256-1:0] xrd;
    generate for (m = 0; m < NXL; m = m + 1) begin : g_xm
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(x_ce), .r_addr_in(x_addr), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(we_q && (|(wm_m[256*m +: 256]))), .w_addr_in(wa_q), .wd_in(wd_m[256*m +: 256]),
            .w_mask_in(wm_m[256*m +: 256]),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---- E4: the column macros' input registers (ot_gpu_sm_v stage 2) ----
    reg              iv_b, iv_f, ifirst, ilast, ifp4, ibf;
    reg [TAGW-1:0]   itag;
    reg [WSW-1:0]    iw;
    reg [SLW-1:0]    ix;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv_b <= 1'b0; iv_f <= 1'b0; end
        else begin iv_b <= c3v[1]; iv_f <= c3v[0]; end
    end
    always @(posedge clk) begin
        ifirst <= c3d[CW-3]; ilast <= c3d[CW-4]; ifp4 <= c3d[CW-5]; ibf <= c3d[CW-6]; itag <= c3d[TAGW-1:0];
        iw <= w3;
        ix <= xrd[SLW-1:0];
    end
    // ---- the column macros ----
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
    generate
        if (LBS == 2 && IL == 8 && TAGW == 16 && TCK != 0) begin : g_hbdk
            ot_hbm_accel_bd_col u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq({ix[266 +: 256], ix[0 +: 256]}),
                .xe({ix[266 + 256 +: 10], ix[256 +: 10]}),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end else if (LBS == 2 && IL == 8 && TAGW == 16) begin : g_hbd
            ot_gpu_bd_col u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq({ix[266 +: 256], ix[0 +: 256]}),
                .xe({ix[266 + 256 +: 10], ix[256 +: 10]}),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end else begin : g_sbd
            wire [LBS*256-1:0] xq_s;
            wire [LBS*10-1:0]  xe_s;
            for (qq = 0; qq < LBS; qq = qq + 1) begin : g_b
                assign xq_s[256*qq +: 256] = ix[qq*266 +: 256];
                assign xe_s[10*qq +: 10]   = ix[qq*266 + 256 +: 10];
            end
            if (TCK != 0) begin : g_k
                ot_hbm_accel_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                    .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                    .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                    .ov(bov), .y(by), .otag(btag), .fault(bfault));
            end else begin : g_o
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            end
        end
        if (LSB == 16 && TAGW == 16 && IL == 8 && TCK != 0) begin : g_hardk
            ot_hbm_accel_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (LSB == 16 && TAGW == 16 && IL == 8) begin : g_hard
            ot_gpu_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (TCK != 0) begin : g_softk
            ot_hbm_accel_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else begin : g_soft
            ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end
    endgenerate
    // ---- G1: this sub's combine-tree input, selected by the op's format (registered with the op) ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gv <= 1'b0; gf <= 1'b0; end
        else begin gv <= bov | fov; gf <= bfault | ffault | (bov & fov); end
    // PQ: select by the column that produced the result (ot_gpu_sm_v's select on the block-dot valid), not by the
    // format of the line now entering the column: under pipelined issue the next op's format reaches E4 while the
    // previous op's results are still leaving the column macros.
    always @(posedge clk) begin
        gy <= (G1ASB != 0) ? (ibf ? fy : by) : (bov ? by : fy);
        gt <= (G1ASB != 0) ? (ibf ? ftag : btag) : (bov ? btag : ftag);
    end
endmodule
