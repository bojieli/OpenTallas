`timescale 1ns/1ps
`default_nettype none
// HC engine bank tile (H-NETLIST/hceng 2026-10-16): systolic term-k stage of the W=256 static HC projection.
// One master, replicated x8 inside ot_hbm_hc_eng_static (bank k = term k of every 8-term chunk).
//   lanes   ot_hdc_v41x_hcp_stage #(W, LG=8): W FP32 MAC lanes in W/8 hard lane leaves ot_hdc_v41x_hcp_lanes
//           (closed leaf, instantiated without overrides by the stage); partial chunk sum of stage k-1 + w*x term k,
//           csum chunk order ((0+t0)+t1)..+t7 op for op (bit-identical to the HCP / tools/hdc_golden_v41 chunk8).
//   weights W/8 ot_sram_1r1w_1024x256 macros, macro g = lanes 8g..8g+7 (binary32): word slot*256 + o*R + r holds
//           fn[o][8(rW + 8g + i) + k], i = 0..7 (4 weight slots of 24 rows x R = 10 runs at K 20,480).
//   x       W/16 ot_sram_1r1w_128x256 macros, macro h = lanes 16h..16h+15 (BF16): word p*R + r holds
//           flat_p[8(rW + 16h + i) + k].
// WRITE PORT (static, from the engine ingress): one 32-chunk wave slice j (lanes 32j..32j+31) per edge:
//   wd[32m +: 32] = term k of wave chunk m (m = 0..31). wv: weight macros 4j..4j+3 take word wa (full words);
//   xv: x macros 2j, 2j+1 take word wa[6:0] (upper BF16 half of each binary32 container).
// Pin registers: every write input and the descriptor/partial sums (inside the stage) land in pin flops; the read
// data is captured raw next to the macros (memory latency ML = 2: address flop -> macro -> capture flop).
// MUT (bench): 1 = weight write slice rotated by one group.
module ot_hbm_hc_bank_static #(
    parameter integer W   = 256,
    parameter integer AW  = 10,
    parameter integer LM  = 8,
    parameter integer LA  = 7,
    parameter integer MUT = 0,
    parameter integer NVW = $clog2(W) + 1
)(
    input  wire              clk, rst_n,
    input  wire              first,
    input  wire              d_v, d_ss,
    input  wire [NVW-1:0]    d_nv,
    input  wire [AW-1:0]     d_wa, d_xa,
    output wire              o_v, o_ss,
    output wire [NVW-1:0]    o_nv,
    output wire [AW-1:0]     o_wa, o_xa,
    input  wire [W*32-1:0]   sum_in,
    output wire [W*32-1:0]   sum_out,
    input  wire              f_in,
    output wire              f_out,
    input  wire              wv, xv,
    input  wire [$clog2(W/32)-1:0] j,
    input  wire [9:0]        wa,
    input  wire [1023:0]     wd
);
    localparam integer NG = W / 8, NX = W / 16, JW = $clog2(W/32);
    initial if (W % 32 != 0 || W < 64) $fatal(1, "bank W must be a multiple of 32, >= 64");
    // ---- write pin registers
    reg wv_q, xv_q; reg [JW-1:0] j_q; reg [9:0] wa_q; reg [1023:0] wd_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin wv_q <= 0; xv_q <= 0; end else begin wv_q <= wv; xv_q <= xv; end
    always @(posedge clk) begin j_q <= j; wa_q <= wa; wd_q <= wd; end
    // ---- the lane stage
    wire w_re, x_re; wire [AW-1:0] w_addr, x_addr;
    reg [W*32-1:0] wdat; reg [W*16-1:0] xdat;
    ot_hdc_v41x_hcp_stage #(.W(W), .AW(AW), .ML(2), .NVW(NVW), .LM(LM), .LA(LA), .SOR(1), .LRST(1), .ADRST(0), .LG(8)) u_st (
        .clk(clk), .rst_n(rst_n), .first(first),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv), .o_wa(o_wa),
        .o_xa(o_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out), .w_re(w_re), .w_addr(w_addr),
        .w_data(wdat), .x_re(x_re), .x_addr(x_addr), .x_data(xdat));
    // ---- weight macros
    wire [W*32-1:0] wq; wire [W*16-1:0] xq;
    genvar g, h, i;
    generate for (g = 0; g < NG; g = g + 1) begin : g_w
        localparam integer GS = (MUT == 1) ? ((g + 1) % NG) : g;          // mutant: slice lands one group off
        wire we = wv_q && (j_q == JW'(GS / 4));
        wire [255:0] d;
        for (i = 0; i < 8; i = i + 1) begin : g_l
            assign d[32*i +: 32] = wd_q[(8*(GS % 4) + i)*32 +: 32];
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(w_re), .r_addr_in(w_addr[9:0]), .rd_out(wq[g*256 +: 256]),
            .w_ce_in(we), .w_addr_in(wa_q), .wd_in(d), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
    end
    for (h = 0; h < NX; h = h + 1) begin : g_x
        wire we = xv_q && (j_q == JW'(h / 2));
        wire [255:0] d;
        for (i = 0; i < 16; i = i + 1) begin : g_l
            assign d[16*i +: 16] = wd_q[(16*(h % 2) + i)*32 + 16 +: 16];
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(x_re), .r_addr_in(x_addr[6:0]), .rd_out(xq[h*256 +: 256]),
            .w_ce_in(we), .w_addr_in(wa_q[6:0]), .wd_in(d), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---- raw capture next to the macros (ML = 2)
    always @(posedge clk) begin wdat <= wq; xdat <= xq; end
endmodule
`default_nettype wire
