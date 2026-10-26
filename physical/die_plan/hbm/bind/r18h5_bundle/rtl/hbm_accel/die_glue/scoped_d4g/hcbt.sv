// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bank_static.sv
`timescale 1ns/1ps
`default_nettype none
// HC engine bank tile (H-NETLIST/hceng 2026-10-16): systolic term-k stage of the W=256 static HC projection.
// One master, replicated x8 inside ot_hbm_hc_eng_static (bank k = term k of every 8-term chunk).
//   lanes   ot_hdc_v41x_hcp_stage__d4g_hcbt #(W, LG=8): W FP32 MAC lanes in W/8 hard lane leaves ot_hdc_v41x_hcp_lanes__d4g_hcbt
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
module ot_hbm_hc_bank_static__d4g_hcbt #(
    parameter integer W   = 256,
    parameter integer AW  = 10,
    parameter integer LM  = 8,
    parameter integer LA  = 7,
    parameter integer MUT = 0,
    // HBM-B-RTL2 (2026-10-17, default 0 = unchanged): 1 = the rst_n port drives only an ot_rst_relay__d4g_hcbt at the bank
    // boundary (synchronous release, +3 edges; the lane leaves' rst_n then comes from a flop inside this tile: the
    // hc_lanes_ref-r4 native rst_n capture 209.0 fix).  Used by the quarter engine ot_hbm_hc_qeng_static.
    parameter integer RST_RELAY = 0,
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
    wire rn_st, rn_w;
    if (RST_RELAY != 0) begin : g_rr
        wire [1:0] rr;
        ot_rst_relay__d4g_hcbt #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
        assign rn_st = rr[0]; assign rn_w = rr[1];
    end else begin : g_nrr
        assign rn_st = rst_n; assign rn_w = rst_n;
    end
    // ---- write pin registers
    reg wv_q, xv_q; reg [JW-1:0] j_q; reg [9:0] wa_q; reg [1023:0] wd_q;
    always @(posedge clk or negedge rn_w) if (!rn_w) begin wv_q <= 0; xv_q <= 0; end else begin wv_q <= wv; xv_q <= xv; end
    always @(posedge clk) begin j_q <= j; wa_q <= wa; wd_q <= wd; end
    // ---- the lane stage
    wire w_re, x_re; wire [AW-1:0] w_addr, x_addr;
    reg [W*32-1:0] wdat; reg [W*16-1:0] xdat;
    ot_hdc_v41x_hcp_stage__d4g_hcbt #(.W(W), .AW(AW), .ML(2), .NVW(NVW), .LM(LM), .LA(LA), .SOR(1), .LRST(1), .ADRST(0), .LG(8)) u_st (
        .clk(clk), .rst_n(rn_st), .first(first),
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

// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankq_term_static.sv
`timescale 1ns/1ps
`default_nettype none
// LH-UNREAD / F-T 2026-10-19: TERMINAL plain ring bank of the HC quarter engine (ring position 7, the chain's LAST bank).
// ot_hbm_hc_bankq_static forwards the chain descriptor (o_v, o_ss, o_nv, o_wa, o_xa; 29 b) to the next bank. Bank 7
// has no next bank: its sum_out/f_out go to bank 0's chain-exit relay (s_i) and nothing reads the descriptor, so the die
// carried 4 x 29 = 116 driven-but-unread bits (held unread class terminal_chain_control). This master is the terminal
// variant: the forward-descriptor PORTS and their CPO face registers do not exist. Everything else is cycle-exact with
// ot_hbm_hc_bankq_static #(CPI, CPO): beat landing, BF16 residual check (wfault), CPI chain landing, the bank stage
// (ot_hbm_hc_bank_static__d4g_hcbt, unchanged), and the CPO registers of sum_out / f_out. Canonical sources stay unchanged.
// The inner bank stage still has its o_* outputs; inside this tile they have no load (stage chain flops sit in the
// hard lane leaves, so they stay inside the leaf; no die-level bit exists any more).
// SAFE-DESIGN checklist (owner 10-19):
//  1 Pins: every input lands in a flop (CPI=1 descriptor/sum/f; beat/write pins as the canonical bank), every remaining
//    output is a flop (CPO=1 sum_out/f_out; wfault sticky flop); reset enters ot_rst_relay__d4g_hcbt (registered release). PASS
//  2 Reach: no new wire; ports are a strict subset of the canonical bank tile (same slot). PASS
//  3 Fanout: no new driver; removed outputs only reduce loads. PASS
//  4 Depth: no logic added; paths identical or removed. PASS
//  5 Storage: unchanged (bank SRAM macros as canonical); 29 face flops removed. PASS
//  6 Floorplan: same tile slot/footprint class as the canonical bank; 29 fewer face pins. PASS (no new kit)
//  7 Clock: single clk root as canonical bank; no new crossing. PASS
//  8 Schedule: static; no cycle added or removed on any retained output (bench: every retained output equal every
//    cycle vs the canonical master). PASS
// MUT (bench only): 0 = production; 3 = f_out inverted at the face (retained-output mutant, must FAIL the bench);
// 1 is passed to the bank stage exactly as the canonical master (weight slice rotate).
module ot_hbm_hc_bankq_term_core__d4g_hcbt #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    input  wire          clk, rst_n, first,
    input  wire          d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, j, input wire [9:0] wa,
    output reg           wfault
);
    wire [0:0] rc;
    ot_rst_relay__d4g_hcbt #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rc));
    reg v_q; reg [1:0] b_q; reg [255:0] d_q; reg [767:0] hold; reg [1023:0] asm_q;
    always @(posedge clk or negedge rc[0]) if (!rc[0]) v_q <= 1'b0; else v_q <= xb_v;
    always @(posedge clk) begin
        b_q <= xb_beat; d_q <= xb_d;
        for (integer b = 0; b < 3; b = b + 1) if (v_q && b_q == 2'(b)) hold[b*256 +: 256] <= d_q;
        asm_q <= {d_q, hold};
    end
    reg lb_q, xv_c;
    always @(posedge clk) begin
        lb_q <= 1'b0;
        for (integer m = 0; m < 32; m = m + 1) if (|asm_q[m*32 +: 16]) lb_q <= 1'b1;
    end
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin xv_c <= 1'b0; wfault <= 1'b0; end
        else begin xv_c <= xv; if (xv_c && lb_q) wfault <= 1'b1; end
    wire c_v, c_ss, c_f; wire [6:0] c_nv; wire [9:0] c_wa, c_xa; wire [2047:0] c_s;
    wire q_f; wire [2047:0] q_s;
    if (CPI != 0) begin : g_cpi
        reg v_r, f_r, ss_r; reg [6:0] nv_r; reg [9:0] wa_r, xa_r; reg [2047:0] s_r;
        always @(posedge clk or negedge rc[0]) if (!rc[0]) begin v_r <= 1'b0; f_r <= 1'b0; end else begin v_r <= d_v; f_r <= f_in; end
        always @(posedge clk) begin ss_r <= d_ss; nv_r <= d_nv; wa_r <= d_wa; xa_r <= d_xa; s_r <= sum_in; end
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {v_r, ss_r, nv_r, wa_r, xa_r, s_r, f_r};
    end else begin : g_ncpi
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {d_v, d_ss, d_nv, d_wa, d_xa, sum_in, f_in};
    end
    wire f_m = (MUT == 3) ? ~q_f : q_f;
    if (CPO != 0) begin : g_cpo   // terminal: only the partial sums and fault flag leave the tile
        reg f_r; reg [2047:0] s_r;
        always @(posedge clk or negedge rc[0]) if (!rc[0]) f_r <= 1'b0; else f_r <= f_m;
        always @(posedge clk) s_r <= q_s;
        assign {sum_out, f_out} = {s_r, f_r};
    end else begin : g_ncpo
        assign {sum_out, f_out} = {q_s, f_m};
    end
    wire t_v, t_ss; wire [6:0] t_nv; wire [9:0] t_wa, t_xa;   // stage forward descriptor: no load in the terminal tile
    ot_hbm_hc_bank_static__d4g_hcbt #(.W(64), .AW(10), .LM(8), .LA(7), .MUT(MUT == 1 ? 1 : 0), .RST_RELAY(1)) u_b (
        .clk(clk), .rst_n(rst_n), .first(first),
        .d_v(c_v), .d_ss(c_ss), .d_nv(c_nv), .d_wa(c_wa), .d_xa(c_xa), .o_v(t_v), .o_ss(t_ss), .o_nv(t_nv),
        .o_wa(t_wa), .o_xa(t_xa), .sum_in(c_s), .sum_out(q_s), .f_in(c_f), .f_out(q_f),
        .wv(wv), .xv(xv), .j(j), .wa(wa), .wd(asm_q));
endmodule

module ot_hbm_hc_bankq_term_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    input  wire          clk, rst_n,
    input  wire          d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, j, input wire [9:0] wa,
    output wire          wfault
);
    ot_hbm_hc_bankq_term_core__d4g_hcbt #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b0),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule
`default_nettype wire

// Scoped source: rtl/hdc/ot_hdc_fastfp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Low-latency binary32 add and multiply (ot_hdc_qadd__d4g_hcbt / ot_hdc_qmul__d4g_hcbt) for the
// decode core's stream unit and special-function pipelines.
//
// Same arithmetic, bit for bit, as the qualified five-stage pipes they stand in
// for -- rtl/proto/ot_fp32_add_rne_pipe.sv and rtl/hdc/ot_hdc_fp32_mul_pipe.sv:
// IEEE RNE with gradual underflow, every zero result canonical +0, a zero
// multiplier operand giving +0, (+-0)+(+-0) = +0, and a nonfinite operand or an
// overflowing result failing closed through `err` with y = 0.  Equivalence is
// checked cycle by cycle against those pipes (rtl/test/tb_hdc_fastfp_equiv.sv).
//
// What is different is depth.  The five-stage pipes are cut around carry
// chains that the synthesis flow maps to ripple logic (a 31-bit magnitude
// compare, 28-bit adds, a 48-bit product sum, the rounding increment); here
// every carry chain is an explicit Kogge-Stone prefix network, the product is a
// carry-save tree, and the leading-zero count is a tree whose exponent-floor
// clamp is a sentinel bit, so each operation is three register stages.
// ---------------------------------------------------------------------------

// W-bit adder with carry-in, Kogge-Stone prefix carries.
module ot_hdc_ksa__d4g_hcbt #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    reg [W:0] g, p, gn, pn;
    integer l, i;
    always @* begin
        g = {a & b, cin};
        p = {a ^ b, 1'b0};
        for (l = 1; l <= W; l = l * 2) begin
            gn = g;
            pn = p;
            for (i = l; i <= W; i = i + 1) begin
                gn[i] = g[i] | (p[i] & g[i - l]);
                pn[i] = p[i] & p[i - l];
            end
            g = gn;
            p = pn;
        end
    end
    assign s = (a ^ b) ^ g[W-1:0];
    assign cout = g[W];
endmodule

// Leading-zero count of a 32-bit word as a tree (n = 32 for zero).
module ot_hdc_lzc32__d4g_hcbt (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule

// 24 x 24 unsigned product in two halves, so a pipeline register can sit in
// the middle of the tree: 24 AND rows, Wallace reduction by vector 3:2
// compressors 24 -> 16 -> 11 -> 8 (ot_hdc_mul24_rows__d4g_hcbt), then 8 -> 6 -> 4 -> 3
// -> 2 and a Kogge-Stone final add (ot_hdc_mul24_sum__d4g_hcbt).  Rows are flat vectors,
// row k in bits [48k +: 48]; a compressor writes its sum to row 2i and its
// carry to row 2i+1.
module ot_hdc_mul24_rows__d4g_hcbt (
    input  wire [23:0]     a,
    input  wire [23:0]     b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;        // {carry, sum} of three rows
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a & {24{b[i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

module ot_hdc_mul24_sum__d4g_hcbt (
    input  wire [48*8-1:0] rows,
    output wire [47:0]     p
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire unused_cout;
    ot_hdc_ksa__d4g_hcbt #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(p), .cout(unused_cout));
endmodule

// ---------------------------------------------------------------------------
// Binary32 add, LATENCY 3, II 1.  Stage for stage:
//   1  decode; |b| > |a| as one 31-bit prefix compare of the encodings; both
//      exponent differences; the smaller significand aligned with a jam
//   2  the add and the subtract (both prefix adders); the add's one-bit
//      renormalize; the cancellation normalize, its shift the leading-zero
//      count of the difference OR a sentinel at the exponent floor
//   3  round to nearest even (prefix increment), encode, the refusals
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_fast__d4g_hcbt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    //: Magnitude order is the integer order of the encodings (a subnormal's
    //: exponent 1 and a normal's hidden bit agree with it), so the swap is one
    //: compare: b[30:0] > a[30:0] exactly when a - b borrows.
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksa__d4g_hcbt #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksa__d4g_hcbt #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksa__d4g_hcbt #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    //: Three guard bits, everything shifted past them OR-ed into the lowest.
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    //: Both alignments, then the pick: when b is the larger b's exponent is
    //: not below a's, so dba is the distance; otherwise dab.
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= bypass;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= bypass_code;
        s1_sub <= a[31] ^ b[31];
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum, dif;
    wire sum_c, dif_c;
    ot_hdc_ksa__d4g_hcbt #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    ot_hdc_ksa__d4g_hcbt #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif), .cout(dif_c));
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    //: The authority normalizes one bit at a time while bit 26 is clear and the
    //: exponent is above 1: the shift is min(lzc, exp - 1).  A one at bit
    //: 26 - (exp - 1) makes the count stop there.
    wire [7:0]  room = s1_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz;
    ot_hdc_lzc32__d4g_hcbt u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz));
    wire [26:0] sub_val = dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksa__d4g_hcbt #(.W(8)) u_esub (.a(s1_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksa__d4g_hcbt #(.W(8)) u_eadd (.a(s1_exp), .b(8'd0), .cin(carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_code <= s1_code; s2_sign <= s1_sign;
        s2_zero <= s1_sub && (dif == 28'd0);
        s2_exp <= s1_sub ? exp_sub : exp_add;
        s2_val <= s1_sub ? sub_val : add_val;
    end

    // -- stage 3 ------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_hcbt #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd), .cout(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s2_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s2_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (s2_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= s2_code; err <= s2_err; end
            else if (s2_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Binary32 multiply, LATENCY 3, II 1.
//   1  decode; subnormal operands normalized (tree LZC); the exponent sum;
//      the partial products and three carry-save levels (24 -> 8 rows)
//   2  the rest of the tree and the prefix final add; both exponent
//      decisions (leading bit 47 or 46) and the subnormal-result alignment
//      masks, all from the exponent sum alone
//   3  the product's top bit picks the decision; align, round, encode, refuse
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_fast__d4g_hcbt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_hcbt u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_hcbt u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    //: The authority's powers: field - 150 for a normal, -149 - shift for a
    //: subnormal (a normal has no leading zero, so the shift is 0 there).
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksa__d4g_hcbt #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));

    //: The first three compressor levels ride in stage 1, after the normalize.
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows__d4g_hcbt u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_rows <= rows;
        s1_power <= power;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [47:0] prod;
    ot_hdc_mul24_sum__d4g_hcbt u_sum (.rows(s1_rows), .p(prod));
    //: floor = power + msb; a subnormal result when floor < -126, and then the
    //: alignment is -(power + 149) whatever the msb, so only the normal path's
    //: fixed alignment (23 or 24) depends on the product.
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    //: sh_sub >= 24 whenever it is used; clamp at 63 (everything below).
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_sign <= s1_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end

    // -- stage 3 ------------------------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_hcbt #(.W(24)) u_rnd (.a(main), .b(24'd0), .cin(rb && (st || main[0])), .s(rnd), .cout(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = is_sub ? (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]})
                              : {s2_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= 32'd0; err <= s2_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd__d4g_hcbt #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_add_fast__d4g_hcbt (unchanged); L > 3 is ot_hdc_fp32_add_lat__d4g_hcbt #(L), bit for bit
    // the same values, with the extra cuts (rtl/hdc/ot_hdc_fp32_add_lat__d4g_hcbt.sv) so no stage carries two prefix adders.
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_add_fast__d4g_hcbt u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul__d4g_hcbt #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_mul_fast__d4g_hcbt (unchanged); L > 3 is ot_hdc_fp32_mul_lat__d4g_hcbt #(L), bit for bit
    // the same values; L >= 5 cuts the four carry-save levels from the 48-bit prefix add (fast stage 2, the lane
    // tile's -180 ps TT path s1_rows -> s2_prod).
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_mul_fast__d4g_hcbt u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_add_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_add_lat__d4g_hcbt #(LAT): the binary32 adder of ot_hdc_fp32_add_fast__d4g_hcbt (rtl/hdc/ot_hdc_fastfp.sv), bit for bit,
// with LAT = 3..6 register stages.  A MEASUREMENT vehicle for the 1.2 GHz @ SS decision (W11, 2026-09-30): the
// same logic is cut at up to three extra boundaries, so the SS fmax against LAT shows the flop overhead.
//   A1  decode, magnitude compare, exponent differences        | cut C_A  (LAT >= 5)
//   A2  both jammed alignments, the swap pick
//   B1  28-bit sum and difference (prefix adders)               | cut C_B  (LAT >= 4)
//   B2  normalise: sentinel LZC, shift, exponent adjust
//   C1  round increment (prefix adder)                          | cut C_C  (LAT >= 6)
//   C2  encode, subnormal, overflow, canonical zero -> y
//   (B2 is cut after the sentinel LZC when LAT >= 7)
// Every prefix adder is ot_hdc_ksadd_k__d4g_hcbt (rtl/hdc/ot_hdc_prefix.sv): (* keep *) Kogge-Stone levels, so ABC cannot
// re-ripple the carries inside a parent block (W13: the plain form closed standalone and failed in context).
// LAT 3 has the cuts of ot_hdc_fp32_add_fast__d4g_hcbt (after A, after B, after C).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_lat__d4g_hcbt #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
    parameter integer CUTS = -1,
    // DRST 0 (fe-push-hphys-1010, opt-in via OT_FP_DATA_NORST): only the valid bits are reset (cuts VB, valid_out);
    // y / err / data cuts are plain flops (consumers qualify them with valid_out).  1: legacy, every stage bit reset.
    parameter integer DRST = `ifdef OT_FP_DATA_NORST 0 `else 1 `endif
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__d4g_hcbt #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut__d4g_hcbt #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__d4g_hcbt #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut__d4g_hcbt #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32__d4g_hcbt u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut__d4g_hcbt #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k__d4g_hcbt #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut__d4g_hcbt #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
endmodule

// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
// VB >= 0 (fe-push-hphys-1010, opt-in): only bit VB (the bundle's valid) is reset; the data bits are plain flops (a wide
// datapath costs no reset fan-out; validity travels on the reset bit).  VB < 0 (default): every bit reset, as before.
module ot_hdc_w11_cut__d4g_hcbt #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

// fixed tops for the hardening sweep
// the W11 serial-domain LAT-4 adder: the LAT-3 cuts plus C_A (after the decode / compare), bit-identical
module ot_hdc_fp32_add_lat4i__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_lat7__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(7)) u (.*);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_mul_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_mul_lat__d4g_hcbt #(LAT): the binary32 multiplier of ot_hdc_fp32_mul_fast__d4g_hcbt (rtl/hdc/ot_hdc_fastfp.sv), bit for
// bit, with LAT = 3..9 register stages (W11 measurement vehicle for 1.2 GHz @ SS; see ot_hdc_fp32_add_lat__d4g_hcbt).
//   S1  decode, subnormal LZC                             | C5 (LAT >= 8; margin rule 2026-10-06)
//       normalise shift                                   | C1 (LAT >= 6)
//       partial products + three carry-save levels, the exponent sum
//   S2  four carry-save levels                            | C2 (LAT >= 5)
//       the 48-bit prefix add; the subnormal masks
//   S3  select, subnormal shift, sticky/round bits        | C3 (LAT >= 4)
//       round increment (prefix add)                      | C4 (LAT >= 7)
//       encode                                            | C6 (LAT >= 9; margin rule 2026-10-06)
//   C7 (LAT >= 10; margin m3 2026-10-06) sits in front of S1: field / zero / non-finite decode | LZC, power
//       refusals -> y
// Every prefix adder is ot_hdc_ksadd_k__d4g_hcbt (rtl/hdc/ot_hdc_prefix.sv, (* keep *) levels).
// Uses ot_hdc_w11_cut__d4g_hcbt (rtl/hdc/ot_hdc_fp32_add_lat__d4g_hcbt.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_lat__d4g_hcbt #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1,
    // KCP > 1 (margin m3, 2026-10-06): the C1 operand register is KCP kept copies (ot_hdc_mul_kcp48__d4g_hcbt), each driving
    // 24/KCP partial products, so the 24-load operand broadcast to the partial-product rows is a local net.  Values
    // identical (every copy captures the same a_n / b_n); no added cycle.  Needs CUT1.
    parameter integer KCP = 1,
    // Opt-in: reset only valid bits at extra cuts; payload is ignored until valid.
    parameter integer DRST = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [68:0] c7;
    ot_hdc_w11_cut__d4g_hcbt #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b, (a[30:23] == 8'd0), (b[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b[30:23] == 8'hff), (a[30:0] == 31'd0) || (b[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_hcbt u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_hcbt u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W1), .CUT(CUT1), .VB(DRST ? -1 : W1-1)) u_c1 (.clk(clk), .rst_n(rst_n),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48__d4g_hcbt u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k__d4g_hcbt #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows__d4g_hcbt u_rows (.a(p_a), .b(p_b), .rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W2), .CUT(CUT2), .VB(DRST ? -1 : W2-1)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_hcbt #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut__d4g_hcbt #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    generate if (DRST != 0) begin : g_output_reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
    end else begin : g_output_valid_reset
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= e_v;
        end
        always @(posedge clk) begin
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end endgenerate
endmodule

module ot_hdc_fp32_mul_lat4__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat6__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat7__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(7)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat9__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(9)) u (.*);
endmodule

// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i__d4g_hcbt (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(5), .CUTS(5)) u (.*);
endmodule

// KCP copy of the C1 operand register: kept (SYNTH_KEEP_MODULES) so equal-D copies are never merged into one driver
module ot_hdc_mul_kcp48__d4g_hcbt (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule

// ot_hdc_mul24_rows__d4g_hcbt with the operands supplied as K copies: partial product i reads copy i*K/24 (identical values)
module ot_hdc_mul24_rows_k__d4g_hcbt #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_prefix.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Explicit log-depth adders (W10, 72f00b86; shared FP primitive copy owned by W11, rtl/hdc/ot_hdc_prefix.sv).
//
// Written as behavioural `a + b` or `a + inc`, yosys/ABC maps these adders as carry ripples (chains of MAJ or
// OR cells) even with ADDER_MAP_FILE cleared: measured at ORFS WC, 0.833 ns, a 28-bit add inside the element
// took 920 ps and a 24-bit rounding increment a chain of ten OR4/OR5 cells (W10 and W13, 2026-09-30).  Here each
// Kogge-Stone prefix level is a (* keep *) net, so synthesis must keep log2(W) levels.
//
// ot_v41_ksadd: s = a + b + cin (W bits), cout.
// ot_v41_inc:   y = a + inc (W bits), co (the carry out of the top bit).
// ---------------------------------------------------------------------------
module ot_hdc_ksadd_k__d4g_hcbt #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule


module ot_hdc_inc_k__d4g_hcbt #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule

// Scoped source: rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HCP) of the re-specified DeepSeek-V4.1
// decode die: docs/ARCH_SPEC_V41.md section 6 item 7, gap-table row
// "hyper-connection projection" (2,048 FP32 MAC lanes).
//
// FUNCTION (tools/hdc_golden_v41.py Model.hc_mixes under R-ARITH "chunk8").
// Per position p, with flat = the BF16 4-copy residual (K = 4 x dim elements)
// and fn the [nout, K] binary32 projection:
//   ss      = csum(mul(flat, flat))                        (the norm's sum of squares)
//   r       = rsqrt(add(div(ss, nf), eps))                  (hdc_golden rsqrt: magic + 3 Newton steps)
//   mix[o]  = mul(csum(mul(fn[o, :], flat)), r)             (o = 0 .. nout-1)
// csum = chunks of 8 contiguous terms summed sequentially from +0, the chunk
// sums added by a pairwise tree padded with +0.  Every operation is one
// binary32 op of rtl/hdc/ot_hdc_fastfp.sv (3-stage add / multiply, RNE,
// gradual underflow, canonical +0) or the IEEE divider ot_hdc_fdiv.  With
// cmd_scale = 0 the engine returns the raw csum dot products (mix[o] =
// csum(...) exactly; the ss task and the scale are skipped).
//
// LANES.  8 groups x W lanes = 8W FP32 MAC lanes (W = 256: 2,048).  A lane is
// one multiplier feeding one adder whose sum re-enters exactly 3 cycles later
// (the add latency), so a lane interleaves 3 chunk accumulations ("slots") and
// retires one multiply-add per cycle.  A TASK is one aligned run of W chunks
// (8W terms) of one accumulation (position p, row o, run r): the W lanes of a
// group each own one chunk of the run.  One task issues per cycle.  Task n
// (issued in cycle n) belongs to group (n div 3) mod 8, slot n mod 3, and its
// term k (k = 0 .. 7) is multiplied in cycle n + 3k (plus a fixed offset): so
// every lane is busy every cycle, the 8 groups are always at 8 DIFFERENT terms
// k, and the chunk sums of exactly one task complete per cycle.
//
// MEMORIES (outside the engine; fixed read latency ML cycles from the
// registered address to the data at the input port, no handshake).  Both are
// banked by term k, so the 8 groups never conflict:
//   weight bank k, word wbase + o*R + r, lane l:  fn[o][8*(r*W + l) + k]      (binary32)
//   x      bank k, word xbase + p*R + r, lane l:  flat_p[8*(r*W + l) + k]     (BF16)
// with R = ceil(nchunk / W) runs, nchunk = K/8, words past the vector ignored
// (lanes l >= nchunk - r*W of the last run are masked to +0 operands).  Bank k
// in cycle c serves the task issued in cycle c - 3k; its data is rotated to
// that task's group (a one-hot AND-OR by the group field the task carries).
//
// REDUCTION, exactly the csum tree.  The W chunk sums of a task enter a
// pipelined pairwise tree of log2(W) adder levels: that is the csum subtree of
// an aligned run of W chunks.  The run sums of one accumulation (r = 0 .. R-1)
// enter the TAIL: TL levels, level l holding one pending left sibling.  At
// level l an event with bit l of r set adds the stored sibling and moves up;
// with bit l clear it is stored and stops -- unless it is the accumulation's
// last run, whose right sibling is all padding, so it moves up unchanged
// (added to +0).  Every addition is the tree's own pair, so the result is
// csum's padded tree bit for bit (padding past pow2(nchunk) only adds +0).
// Requires R <= 2^TL (fault otherwise) and K a multiple of 8.
//
// ORDER.  Positions p = 0 .. npos-1; per position the ss task run (if
// cmd_scale) then rows o = 0 .. nout-1, each its R runs.  Raw sums enter a
// DF-entry FIFO; issue reserves an entry per accumulation (credit), so the
// engine never drops a result.  The scalar unit turns ss into r (one fdiv,
// one add, one multiply, sequenced: ~90 cycles per position, while the rows
// of that position accumulate), and each raw row sum leaves through one
// multiplier as mix = raw * r (raw * 1.0 = raw when cmd_scale = 0).
//
// PROTOCOL.  cmd_valid/cmd_ready: one command at a time (cmd_ready rises again
// after the command's last result is accepted).  o_valid/o_ready: results in
// (p, o) order, o_last on the command's final result.  Every output is a flop;
// every input is registered before use.  fault (sticky per command): a
// nonfinite operand or overflow anywhere, a divide fault, or R > 2^TL.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_hcp__d4g_hcbt #(
    parameter integer W    = 8,         // lanes per group (power of two >= 2); lanes = 8W (spec: W = 256)
    parameter integer TL   = 9,         // tail levels: runs per accumulation R <= 2^TL (spec: 4)
    parameter integer PMAX = 8,         // positions per command (power of two)
    parameter integer OMAX = 32,        // rows per position (power of two)
    parameter integer AW   = 16,        // bank word address width
    parameter integer CW   = 16,        // chunk-count width (nchunk = K/8)
    parameter integer ML   = 2,         // memory read latency
    parameter integer DF   = 32,        // raw-result FIFO depth (power of two)
    // el1011-hcvm-hc SYSTOLIC lanes (opt-in, default off; cycles change): SYS = 1 builds no lane groups and no bank
    // rotation.  The 8W lanes live outside in 8 bank stages (ot_hdc_v41x_hcp_stage__d4g_hcbt, one per bank, chained): the task
    // descriptor leaves on sd_* (tap 0), stage k multiplies term k from its OWN bank and adds it to the partial chunk
    // sum of stage k - 1 (stage 0 adds to +0), so csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op; stage
    // 7's W chunk sums come back on sys_sum SYS_LAT cycles after tap 0 (the tree leaves at tap SYS_LAT + 1).
    parameter integer SYS  = 0,
    parameter integer SYS_LAT = 0,
    parameter integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1,
    parameter integer OXW  = (OMAX > 1) ? $clog2(OMAX) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // command
    input  wire              cmd_valid,
    output reg               cmd_ready,
    input  wire [PW:0]       cmd_npos,          // 1 .. PMAX
    input  wire [OXW:0]      cmd_nout,          // 1 .. OMAX
    input  wire [CW-1:0]     cmd_nchunk,        // K / 8, >= 1
    input  wire              cmd_scale,
    input  wire [31:0]       cmd_nf,            // binary32 of K (the mean's divisor)
    input  wire [31:0]       cmd_eps,
    input  wire [AW-1:0]     cmd_wbase,
    input  wire [AW-1:0]     cmd_xbase,
    // weight banks (binary32) and x banks (BF16), bank k at [k*...]
    output reg  [7:0]        w_re,
    output reg  [8*AW-1:0]   w_addr,
    input  wire [8*W*32-1:0] w_data,
    output reg  [7:0]        x_re,
    output reg  [8*AW-1:0]   x_addr,
    input  wire [8*W*16-1:0] x_data,
    // results
    output reg               o_valid,
    input  wire              o_ready,
    output reg  [PW-1:0]     o_pos,
    output reg  [OXW-1:0]    o_idx,
    output reg  [31:0]       o_data,
    output reg               o_last,
    output reg               fault,
    output reg               idle,
    // SYS = 1: the descriptor to stage 0, the chunk sums and lane faults back from stage 7
    output wire              sd_v,
    output wire              sd_ss,
    output wire [$clog2(W):0] sd_nv,
    output wire [AW-1:0]     sd_wa,
    output wire [AW-1:0]     sd_xa,
    input  wire [W*32-1:0]   sys_sum,
    input  wire              sys_fault
);
    localparam integer LW  = $clog2(W);
    localparam integer NVW = LW + 1;
    localparam integer DFW = $clog2(DF);
    // descriptor fields
    localparam integer F_V   = 0;
    localparam integer F_SS  = 1;
    localparam integer F_LR  = 2;                 // last run
    localparam integer F_GRP = 3;                 // 3 bits
    localparam integer F_NV  = 6;                 // NVW bits
    localparam integer F_WA  = F_NV + NVW;
    localparam integer F_XA  = F_WA + AW;
    localparam integer F_POS = F_XA + AW;
    localparam integer F_IDX = F_POS + PW;
    localparam integer F_R   = F_IDX + OXW;       // TL low bits of the run index
    localparam integer F_LO  = F_R + TL;          // last output of the command
    localparam integer DW    = F_LO + 1;
    // pipeline taps (descriptor delay-line index of the task a stage holds)
    localparam integer T_OP   = 21 + ML + 3;                 // group operands of term 7
    localparam integer T_LEAF = SYS ? SYS_LAT + 1 : 31 + ML; // tree leaves
    localparam integer T_TAIL = T_LEAF + 3 * LW;             // tree output = tail level 0 input
    localparam integer NDL    = T_TAIL + 3 * TL + 1;

    genvar gk, gg, gl, gv;
    integer i;

    // ------------------------------------------------------------------ command / issue
    reg              busy, active;
    reg [PW:0]       npos_r;
    reg [OXW:0]      nout_r;
    reg [CW-1:0]     nrun_r, nlast_r;              // runs per accumulation; lanes of the last run
    reg              scale_r;
    reg [31:0]       nf_r, eps_r;
    reg [PW-1:0]     p;
    reg [OXW-1:0]    o;
    reg              ssph;
    reg [CW-1:0]     r;
    reg [AW-1:0]     wbase_r, wcur, xpos;
    reg [4:0]        ph24;                          // free-running cycle mod 24
    reg [DFW:0]      acc_cnt;                       // accumulations reserved, not yet popped
    wire             pop_raw;
    wire [CW-1:0]    nrun_c = (cmd_nchunk + W - 1) >> LW;
    wire             first_r = (r == 0);
    wire             last_r = (r == nrun_r - 1'b1);
    wire             credit = (acc_cnt < DF);
    wire             iss = active && (!first_r || credit);
    wire             last_o = ssph ? 1'b0 : ({1'b0, o} == nout_r - 1'b1);
    wire             last_p = ({1'b0, p} == npos_r - 1'b1);
    reg  [DW-1:0]    d0;
    wire             tl_over_c = (nrun_c > (1 << TL));
    localparam [NVW-1:0] WNV = W;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; active <= 1'b0; cmd_ready <= 1'b0; ph24 <= 5'd0; acc_cnt <= 0;
        end else begin
            ph24 <= (ph24 == 5'd23) ? 5'd0 : ph24 + 5'd1;
            cmd_ready <= !busy && !(cmd_valid && cmd_ready);
            acc_cnt <= acc_cnt + (iss && first_r) - pop_raw;
            if (cmd_valid && cmd_ready) begin
                busy <= 1'b1; active <= 1'b1;
            end else if (iss && last_r && last_o && last_p) begin
                active <= 1'b0;
            end
            if (o_valid && o_ready && o_last) busy <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (cmd_valid && cmd_ready) begin
            npos_r <= cmd_npos; nout_r <= cmd_nout; scale_r <= cmd_scale;
            nrun_r <= nrun_c; nlast_r <= ((cmd_nchunk - 1'b1) & (W - 1)) + 1'b1;
            nf_r <= cmd_nf; eps_r <= cmd_eps; wbase_r <= cmd_wbase;
            p <= 0; o <= 0; r <= 0; ssph <= cmd_scale; wcur <= cmd_wbase; xpos <= cmd_xbase;
        end else if (iss) begin
            if (!last_r) r <= r + 1'b1;
            else begin
                r <= 0;
                if (ssph) ssph <= 1'b0;
                else if (!last_o) o <= o + 1'b1;
                else begin
                    o <= 0; p <= p + 1'b1; ssph <= scale_r; wcur <= wbase_r; xpos <= xpos + nrun_r;
                end
            end
            if (!ssph && !(last_r && last_o)) wcur <= wcur + 1'b1;
        end
        // the task descriptor entering the delay line (a bubble still carries its group)
        d0 <= {DW{1'b0}};
        d0[F_V] <= iss;
        d0[F_SS] <= ssph;
        d0[F_LR] <= last_r;
        d0[F_GRP +: 3] <= ph24 / 3;
        d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;
        d0[F_WA +: AW] <= wcur;
        d0[F_XA +: AW] <= xpos + r;
        d0[F_POS +: PW] <= p;
        d0[F_IDX +: OXW] <= o;
        d0[F_R +: TL] <= r[TL-1:0];
        d0[F_LO] <= !ssph && last_o && last_p;
    end
    // delay line: dl[i] = d0 delayed i cycles (dl[0] = d0); the valid bit is reset
    reg  [NDL-1:0]        dlv;                      // valid bits (reset)
    reg  [(DW-1)*NDL-1:0] dld;                      // the other fields (no reset)
    wire [DW*(NDL+1)-1:0] dl;
    assign dl[DW-1:0] = d0;
    generate for (gv = 0; gv < NDL; gv = gv + 1) begin : g_dl
        assign dl[DW*(gv+1) +: DW] = {dld[(DW-1)*gv +: DW-1], dlv[gv]};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) dlv <= {NDL{1'b0}};
        else for (i = 0; i < NDL; i = i + 1) dlv[i] <= dl[DW*i + F_V];
    end
    always @(posedge clk)
        for (i = 0; i < NDL; i = i + 1) dld[(DW-1)*i +: DW-1] <= dl[DW*i + 1 +: DW-1];

    // ------------------------------------------------------------------ bank addresses (term k at tap 3k)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_re <= 8'd0; x_re <= 8'd0; end
        else for (i = 0; i < 8; i = i + 1) begin
            w_re[i] <= dl[DW*(3*i) + F_V] && !dl[DW*(3*i) + F_SS];
            x_re[i] <= dl[DW*(3*i) + F_V];
        end
    end
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1) begin
            w_addr[AW*i +: AW] <= dl[DW*(3*i) + F_WA +: AW];
            x_addr[AW*i +: AW] <= dl[DW*(3*i) + F_XA +: AW];
        end

    reg [W*32-1:0] leaf;
    reg            leaf_v;
    wire           lane_fault_any;
    assign sd_v = d0[F_V]; assign sd_ss = d0[F_SS]; assign sd_nv = d0[F_NV +: NVW]; assign sd_wa = d0[F_WA +: AW];
    assign sd_xa = d0[F_XA +: AW];
    generate if (SYS == 0) begin : g_flat
    // ------------------------------------------------------------------ input registers
    reg [8*W*32-1:0] w_in;
    reg [8*W*16-1:0] x_in;
    always @(posedge clk) begin
        w_in <= w_data;
        x_in <= x_data;
    end

    // ------------------------------------------------------------------ rotation to groups, masking
    // bank k's input register holds the task at tap 3k + 2 + ML
    wire [63:0] sel;                                  // sel[8g + k]
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_sel
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            //: qualified by the task's valid bit: a bubble's group field may be stale (the delay line's data
            //: bits carry no reset), and only valid tasks are guaranteed one per group
            assign sel[8*gg + gk] = dl[DW*(3*gk + 2 + ML) + F_V] && (dl[DW*(3*gk + 2 + ML) + F_GRP +: 3] == gg);
        end
    end

    reg  [7:0]        gfirst, glast;                // first: a = +0 (term 0, or no task)
    reg  [7:0]        gov;                          // the group holds a task's operands
    wire [8*W-1:0]    lane_fault;
    wire [8*W*32-1:0] gsum;
    reg  [7:0]        lastv [0:6];                  // group's last-term flag, delayed 0..6 from gw
    reg  [7:0]        fst   [0:3];                  // group's first flag, delayed 0..3
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_grp
        reg          ov, oss;
        reg [NVW-1:0] onv;
        reg [W*32-1:0] ow;
        reg [W*16-1:0] ox;
        integer k2;
        always @(*) begin
            ov = 1'b0; oss = 1'b0; onv = {NVW{1'b0}}; ow = {(W*32){1'b0}}; ox = {(W*16){1'b0}};
            for (k2 = 0; k2 < 8; k2 = k2 + 1) begin
                ov  = ov  | sel[8*gg + k2];
                oss = oss | (sel[8*gg + k2] & dl[DW*(3*k2 + 2 + ML) + F_SS]);
                onv = onv | ({NVW{sel[8*gg + k2]}} & dl[DW*(3*k2 + 2 + ML) + F_NV +: NVW]);
                ow  = ow  | ({(W*32){sel[8*gg + k2]}} & w_in[W*32*k2 +: W*32]);
                ox  = ox  | ({(W*16){sel[8*gg + k2]}} & x_in[W*16*k2 +: W*16]);
            end
        end
        for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
            wire        lv = ov && (gl < onv);
            wire [31:0] xw = {ox[16*gl +: 16], 16'h0000};
            reg  [31:0] gx, gw;                    // the lane's operands (lane-local registers)
            always @(posedge clk) begin
                gx <= lv ? xw : 32'd0;
                gw <= lv ? (oss ? xw : ow[32*gl +: 32]) : 32'd0;
            end
            // the lane: product, then the 3-slot interleaved accumulation
            wire [31:0] prod, sum;
            wire [1:0]  e0, e1;
            wire        v0, v1;
            ot_hdc_fp32_mul_fast__d4g_hcbt u_mul (.clk(clk), .rst_n(rst_n), .valid_in(gov[gg]),
                                        .a(gw), .b(gx),
                                        .y(prod), .err(e0), .valid_out(v0));
            ot_hdc_fp32_add_fast__d4g_hcbt u_add (.clk(clk), .rst_n(rst_n), .valid_in(v0),
                                        .a(fst[2][gg] ? 32'd0 : sum), .b(prod),
                                        .y(sum), .err(e1), .valid_out(v1));
            assign gsum[32*(W*gg + gl) +: 32] = sum;
            //: errors count only on a task's terms (the valid chains ride the units' own pipes)
            assign lane_fault[W*gg + gl] = (v0 && (|e0)) || (v1 && (|e1));
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) gov[gg] <= 1'b0; else gov[gg] <= ov;
        always @(posedge clk) begin
            gfirst[gg] <= sel[8*gg + 0] || !ov;
            glast[gg]  <= sel[8*gg + 7];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 7; i = i + 1) lastv[i] <= 8'd0;
        end else begin
            lastv[0] <= glast;
            for (i = 1; i < 7; i = i + 1) lastv[i] <= lastv[i-1];
        end
    end
    always @(posedge clk) begin
        fst[0] <= gfirst;
        for (i = 1; i < 4; i = i + 1) fst[i] <= fst[i-1];
    end
    //: fst[2] is the first flag of the term whose product the adder takes now;
    //: lastv[5] marks the group whose adder output is a finished chunk sum.
    wire [7:0] done_g = lastv[5];

    // ------------------------------------------------------------------ tree over the W chunk sums
    integer g3;
    always @(posedge clk) begin
        leaf <= {(W*32){1'b0}};
        for (g3 = 0; g3 < 8; g3 = g3 + 1)
            if (done_g[g3]) leaf <= gsum[W*32*g3 +: W*32];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= |done_g;
    end
    assign lane_fault_any = |lane_fault;
    end else begin : g_sys
    // the stage chain is outside: stage 7's chunk sums of the task at tap T_LEAF - 1 arrive on sys_sum now
    always @(posedge clk) leaf <= dl[DW*(T_LEAF-1) + F_V] ? sys_sum : {(W*32){1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= dl[DW*(T_LEAF-1) + F_V];
    assign lane_fault_any = sys_fault;
    end endgenerate
    wire [31:0] root;
    wire        tree_fault;
    wire        tree_vo;
    ot_hdc_v41x_addtree__d4g_hcbt #(.N(W)) u_tree (.clk(clk), .rst_n(rst_n), .v(leaf_v), .x(leaf), .y(root), .vo(tree_vo),
                                         .fault(tree_fault));
    wire [LW*3:0] tvv;
    ot_hdc_v41x_vline__d4g_hcbt #(.D(3*LW)) u_tvv (.clk(clk), .rst_n(rst_n), .v(leaf_v), .vd(tvv));

    // ------------------------------------------------------------------ tail: pairwise tree over runs
    wire [32*(TL+1)-1:0] ev_val;
    wire [TL:0]          ev_v;
    wire [TL-1:0]        tail_fault;
    assign ev_val[31:0] = root;
    assign ev_v[0] = tvv[3*LW];
    generate for (gv = 0; gv < TL; gv = gv + 1) begin : g_tail
        localparam integer TAP = T_TAIL + 3 * gv;
        wire bitl  = dl[DW*TAP + F_R + gv];
        wire lastr = dl[DW*TAP + F_LR];
        wire go    = ev_v[gv] && (bitl || lastr);
        reg [31:0] slot;
        always @(posedge clk) if (ev_v[gv] && !bitl && !lastr) slot <= ev_val[32*gv +: 32];
        wire [1:0] e;
        ot_hdc_fp32_add_fast__d4g_hcbt u_a (.clk(clk), .rst_n(rst_n), .valid_in(go),
                                  .a(bitl ? slot : 32'd0), .b(ev_val[32*gv +: 32]),
                                  .y(ev_val[32*(gv+1) +: 32]), .err(e), .valid_out(ev_v[gv+1]));
        assign tail_fault[gv] = ev_v[gv+1] && (|e);
    end endgenerate
    localparam integer T_RAW = T_TAIL + 3 * TL;
    wire raw_v   = ev_v[TL] && dl[DW*T_RAW + F_LR];
    wire raw_bad = ev_v[TL] && !dl[DW*T_RAW + F_LR];      // R > 2^TL

    // ------------------------------------------------------------------ raw-result FIFO
    localparam integer RQW = 1 + 1 + PW + OXW + 32;       // {last out, ss, pos, idx, value}
    reg  [RQW-1:0] rq [0:DF-1];
    reg  [DFW:0]   rq_wp, rq_rp;
    wire           rq_ne = (rq_wp != rq_rp);
    wire [RQW-1:0] rq_h = rq[rq_rp[DFW-1:0]];
    reg  [RQW-1:0] raw_w;
    reg            raw_wv;
    always @(posedge clk) begin
        raw_w <= {dl[DW*(T_RAW) + F_LO], dl[DW*(T_RAW) + F_SS], dl[DW*(T_RAW) + F_POS +: PW],
                  dl[DW*(T_RAW) + F_IDX +: OXW], ev_val[32*TL +: 32]};
        if (raw_wv) rq[rq_wp[DFW-1:0]] <= raw_w;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rq_wp <= 0; rq_rp <= 0; raw_wv <= 1'b0; end
        else begin
            raw_wv <= raw_v;
            if (raw_wv) rq_wp <= rq_wp + 1'b1;
            if (pop_raw) rq_rp <= rq_rp + 1'b1;
        end
    end
    wire          h_lo  = rq_h[RQW-1];
    wire          h_ss  = rq_h[RQW-2];
    wire [PW-1:0] h_pos = rq_h[32 + OXW +: PW];
    wire [OXW-1:0] h_idx = rq_h[32 +: OXW];
    wire [31:0]   h_val = rq_h[31:0];

    // ------------------------------------------------------------------ scalar r unit
    reg  [31:0]     rv [0:PMAX-1];
    reg  [PMAX-1:0] r_ok;
    reg  [3:0]      st;
    reg             pend;
    reg  [1:0]      it;
    reg  [PW-1:0]   rs_pos;
    reg  [31:0]     rs_q, rs_h, rs_y, rs_a;
    localparam [3:0] S_IDLE = 4'd0, S_DIV = 4'd1, S_EPS = 4'd2, S_HALF = 4'd3, S_YY = 4'd4, S_HY = 4'd5,
                     S_SUB = 4'd6, S_MY = 4'd7;
    wire rs_take = rq_ne && h_ss && (st == S_IDLE);
    // units
    reg         dv, av, mv;
    reg  [31:0] da, db, aa, ab, ma, mb;
    wire [31:0] dy, ay, my;
    wire        dvo, avo, mvo, dfl;
    wire [1:0]  aerr, merr;
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(dv), .a(da), .b(db), .y(dy), .vo(dvo), .fault(dfl));
    ot_hdc_fp32_add_fast__d4g_hcbt u_sa (.clk(clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay), .err(aerr),
                               .valid_out(avo));
    ot_hdc_fp32_mul_fast__d4g_hcbt u_sm (.clk(clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my), .err(merr),
                               .valid_out(mvo));
    wire rs_fault = (dvo && dfl) || (avo && (|aerr)) || (mvo && (|merr));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pend <= 1'b0; dv <= 1'b0; av <= 1'b0; mv <= 1'b0; r_ok <= {PMAX{1'b0}};
        end else begin
            dv <= 1'b0; av <= 1'b0; mv <= 1'b0;
            if (cmd_valid && cmd_ready) r_ok <= {PMAX{1'b0}};
            case (st)
                S_IDLE: if (rs_take) begin st <= S_DIV; pend <= 1'b0; end
                S_DIV:  if (!pend) begin dv <= 1'b1; pend <= 1'b1; end
                        else if (dvo) begin pend <= 1'b0; st <= S_EPS; end
                S_EPS:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_HALF; end
                S_HALF: if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_YY; end
                S_YY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_HY; end
                S_HY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_SUB; end
                S_SUB:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_MY; end
                S_MY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin
                            pend <= 1'b0;
                            if (it == 2'd2) begin st <= S_IDLE; r_ok[rs_pos] <= 1'b1; end
                            else st <= S_YY;
                        end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == S_IDLE && rs_take) begin
            rs_pos <= h_pos; da <= h_val; db <= nf_r; it <= 2'd0;
        end
        if (st == S_DIV && pend && dvo) begin aa <= dy; ab <= eps_r; end
        if (st == S_EPS && pend && avo) begin
            ma <= ay; mb <= 32'h3F000000;                         // half = v * 0.5
            rs_y <= 32'h5F3759DF - {1'b0, ay[31:1]};              // y0 from v's bits
        end
        if (st == S_HALF && pend && mvo) begin rs_h <= my; ma <= rs_y; mb <= rs_y; end
        if (st == S_YY && pend && mvo) begin ma <= rs_h; mb <= my; end
        if (st == S_HY && pend && mvo) begin aa <= 32'h3FC00000; ab <= {~my[31], my[30:0]}; end
        if (st == S_SUB && pend && avo) begin ma <= rs_y; mb <= ay; end
        if (st == S_MY && pend && mvo) begin
            rs_y <= my; ma <= my; mb <= my; it <= it + 1'b1;
            if (it == 2'd2) rv[rs_pos] <= my;
        end
    end

    // ------------------------------------------------------------------ output: raw * r
    localparam integer OQ = 8;
    localparam integer OTW = 1 + PW + OXW;
    reg  [3:0]  oinf;                                 // products in flight
    reg  [3:0]  ocnt;
    wire        o_room = ({1'b0, oinf} + {1'b0, ocnt} + {4'd0, o_valid}) < OQ;
    wire        h_ok = !scale_r || r_ok[h_pos];
    wire        take_out = rq_ne && !h_ss && h_ok && o_room;
    assign pop_raw = rs_take || take_out;
    reg         ov_in;
    reg  [31:0] oa, ob;
    reg  [OTW-1:0] otag_in;
    wire [31:0] oy;
    wire [1:0]  oerr;
    wire        ovo;
    wire [OTW-1:0] otag;
    ot_hdc_fp32_mul_fast__d4g_hcbt u_om (.clk(clk), .rst_n(rst_n), .valid_in(ov_in), .a(oa), .b(ob), .y(oy), .err(oerr),
                               .valid_out(ovo));
    ot_hdc_delay #(.W(OTW), .D(3)) u_otag (.clk(clk), .rst_n(rst_n), .d(otag_in), .q(otag));
    reg  [OTW+31:0] oq [0:OQ-1];
    reg  [3:0]      oq_wp, oq_rp;
    wire            oq_ne = (oq_wp != oq_rp);
    wire            o_load = oq_ne && (!o_valid || o_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_in <= 1'b0; oinf <= 4'd0; ocnt <= 4'd0; oq_wp <= 4'd0; oq_rp <= 4'd0; o_valid <= 1'b0;
        end else begin
            ov_in <= take_out;
            oinf <= oinf + {3'd0, take_out} - {3'd0, ovo};
            ocnt <= ocnt + {3'd0, ovo} - {3'd0, o_load};
            if (ovo) oq_wp <= (oq_wp == OQ - 1) ? 4'd0 : oq_wp + 4'd1;
            if (o_load) oq_rp <= (oq_rp == OQ - 1) ? 4'd0 : oq_rp + 4'd1;
            if (o_load) o_valid <= 1'b1;
            else if (o_ready) o_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (take_out) begin
            oa <= h_val; ob <= scale_r ? rv[h_pos] : 32'h3F800000; otag_in <= {h_lo, h_pos, h_idx};
        end
        if (ovo) oq[oq_wp] <= {otag, oy};
        if (o_load) {o_last, o_pos, o_idx, o_data} <= oq[oq_rp];
    end

    // ------------------------------------------------------------------ fault, idle
    reg lf_r, tf_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; idle <= 1'b1; lf_r <= 1'b0; tf_r <= 1'b0; end
        else begin
            lf_r <= lane_fault_any;
            tf_r <= tree_fault || (|tail_fault) || raw_bad || rs_fault || (ovo && (|oerr));
            if (cmd_valid && cmd_ready) fault <= tl_over_c;
            else if (lf_r || tf_r) fault <= 1'b1;
            idle <= !busy;
        end
    end
endmodule

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_v41x_vline__d4g_hcbt #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    generate if (D == 0) begin : g0
        assign vd = v;
    end else begin : gd
        reg [D-1:0] line;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) line <= {D{1'b0}};
            else line <= (line << 1) | {{(D-1){1'b0}}, v};
        end
        assign vd = {line, v};
    end endgenerate
endmodule

// Pairwise tree ((x0 + x1) + (x2 + x3)) + ... over N binary32 inputs (N a power
// of two), one ot_hdc_fp32_add_fast__d4g_hcbt per node, 3 cycles per level, II 1.  v
// travels with the operands (vo = v delayed 3 log2 N); a node's error counts
// only on a valid pass, and fault is registered one cycle after it.
module ot_hdc_v41x_addtree__d4g_hcbt #(parameter integer N = 2) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [N*32-1:0] x,
    output wire [31:0]   y,
    output wire          vo,
    output reg           fault
);
    wire [1:0] e;
    generate if (N == 1) begin : g_one
        assign y = x;
        assign vo = v;
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= 1'b0;
    end else if (N == 2) begin : g_two
        ot_hdc_fp32_add_fast__d4g_hcbt u_a (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(x[31:0]), .b(x[63:32]), .y(y),
                                  .err(e), .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= vo && (|e);
    end else begin : g_rec
        wire [31:0] yl, yr;
        wire        fl, fr, vl, vr;
        ot_hdc_v41x_addtree__d4g_hcbt #(.N(N / 2)) u_l (.clk(clk), .rst_n(rst_n), .v(v), .x(x[0 +: N*16]), .y(yl), .vo(vl),
                                               .fault(fl));
        ot_hdc_v41x_addtree__d4g_hcbt #(.N(N / 2)) u_r (.clk(clk), .rst_n(rst_n), .v(v), .x(x[N*16 +: N*16]), .y(yr), .vo(vr),
                                               .fault(fr));
        ot_hdc_fp32_add_fast__d4g_hcbt u_a (.clk(clk), .rst_n(rst_n), .valid_in(vl), .a(yl), .b(yr), .y(y), .err(e),
                                  .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= (vo && (|e)) || fl || fr;
    end endgenerate
endmodule

// el1011-hcvm-hc: one SYSTOLIC bank stage of the HCP (SYS = 1).  Stage k holds W FP32 MAC lanes beside bank k's
// weight and x memories.  The task descriptor enters through pin flops (local cycle 0 = the flat engine's tap 3k),
// addresses its own bank (registered, local 1), takes the data ML cycles later (local 1 + ML) into input registers,
// forms the masked lane operands (local 3 + ML), multiplies (3 stages) and adds the product to the partial chunk sum
// that stage k - 1 hands over (pin flop, local 6 + ML; stage 0 adds to +0 through the `first` strap): the term order of
// csum is the flat engine's ((0 + t0) + t1) .. + t7, one binary32 op each, so the chunk sums are bit-identical.  The
// descriptor leaves after 3 registers (the next stage's pin flop makes the hop 4 cycles), the partial sums leave from
// the adder's output register, the lane-fault flag from a register.  No datapath register carries a reset; the
// per-lane operand enables are replicated kept registers (one per lane, no select net over all 32 lanes).
module ot_hdc_v41x_hcp_stage__d4g_hcbt #(
    parameter integer W   = 8,
    parameter integer AW  = 16,
    parameter integer ML  = 2,
    parameter integer NVW = $clog2(W) + 1,
    // pipelined IEEE units (1.2 GHz: 8-stage multiply, 7-stage add, ot_hdc_fp32_*_lat, bit for bit the fast units);
    // the stage hop is LA + 1 cycles (adder output register -> next stage's pin flop)
    parameter integer LM  = 8,
    parameter integer LA  = 7,
    // el1011-hbm-hcvm/hc round 3 (hc_tile-sys-048ca3d9e-b: rst relay -> u_add.y RESETN -310 ps, add y -> sum_out
    // pin -162 ps wire): SOR 1 registers sum_out at the seam (hop LA + 1 + SOR); LRST 1 gives every lane its own kept
    // reset flop (no rst_n net over 32 lanes' fp pipes); ADRST 0 builds the adders with data-bit reset off (valid only)
    parameter integer SOR = 0,
    parameter integer LRST = 0,
    parameter integer ADRST = 1,
    // el1011-hbm-hcvm/hc round 4 (hc_tile-sys-faa39cbe9-b EARLY_FAIL_HOLD: ONE clock root over 56,560 sinks, avg sink wire
    // 538 um, FF insertion 415..682 ps -> hold stuck at -165 ps inside u_mul pipes; textbook REFUSE > 15k sinks/root):
    // LG 8 = the lanes live in W/8 HARD lane-group leaves (ot_hdc_v41x_hcp_lanes__d4g_hcbt, own clock tree, ~13k sinks each);
    // the leaf's pin flops ARE the old input registers (w_in, x_in, sum_q, lv_r/ss_r, gov, fst_q) and its outputs are
    // the adder/seam registers + the registered group fault, so every latency is unchanged (SYS_LAT unchanged).
    parameter integer LG = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              first,
    input  wire              d_v,
    input  wire              d_ss,
    input  wire [NVW-1:0]    d_nv,
    input  wire [AW-1:0]     d_wa,
    input  wire [AW-1:0]     d_xa,
    output wire              o_v,
    output wire              o_ss,
    output wire [NVW-1:0]    o_nv,
    output wire [AW-1:0]     o_wa,
    output wire [AW-1:0]     o_xa,
    input  wire [W*32-1:0]   sum_in,
    output wire [W*32-1:0]   sum_out,
    input  wire              f_in,
    output reg               f_out,
    output reg               w_re,
    output reg  [AW-1:0]     w_addr,
    input  wire [W*32-1:0]   w_data,
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [W*16-1:0]   x_data
);
    localparam integer NC = (1 + ML > LA + SOR) ? 1 + ML : LA + SOR;   // descriptor delay taps kept locally
    localparam integer DW = 2 + NVW + 2 * AW;
    reg  [NC:0]      cv;                                         // valid, taps 0..NC (reset)
    reg  [DW-2:0]    cd [0:NC];                                  // other fields (no reset)
    reg              fin_q;
    wire             lf_any;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cv <= '0; w_re <= 1'b0; x_re <= 1'b0; fin_q <= 1'b0; f_out <= 1'b0; end
        else begin
            cv <= {cv[NC-1:0], d_v};
            w_re <= cv[0] && !cd[0][DW-2];
            x_re <= cv[0];
            fin_q <= f_in;
            f_out <= fin_q || lf_any;
        end
    end
    always @(posedge clk) begin
        cd[0] <= {d_ss, d_nv, d_wa, d_xa};
        for (integer j = 1; j <= NC; j = j + 1) cd[j] <= cd[j-1];
        w_addr <= cd[0][2*AW-1:AW];
        x_addr <= cd[0][AW-1:0];
    end
    assign o_v = cv[LA + SOR]; assign {o_ss, o_nv, o_wa, o_xa} = cd[LA + SOR]; // tap j = local j: out at local LA + SOR
    generate if (LG == 0) begin : g_flat
    reg fst_q, gov, lf_q;
    assign lf_any = lf_q;
    always @(posedge clk) fst_q <= first;
    // input registers (local 2 + ML) and the per-lane enables of that task (computed a cycle early, replicated)
    reg [W*32-1:0] w_in; reg [W*16-1:0] x_in;
    (* keep = "true" *) reg [W-1:0] lv_r, ss_r;
    reg ov_r;
    wire [NVW-1:0] nv_e = cd[1 + ML][DW-3 -: NVW];               // the task at local 1 + ML
    always @(posedge clk) begin
        w_in <= w_data; x_in <= x_data;
        for (integer l = 0; l < W; l = l + 1) begin
            lv_r[l] <= cv[1 + ML] && (l < nv_e);
            ss_r[l] <= cd[1 + ML][DW-2];
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
    reg [W*32-1:0] sum_q;
    always @(posedge clk) sum_q <= sum_in;
    wire [W-1:0] lfl;
    wire [W*32-1:0] y_l;
    if (SOR != 0) begin : g_sor
        reg [W*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign sum_out = so_q;
    end else begin : g_nsor
        assign sum_out = y_l;
    end
    for (genvar gl = 0; gl < W; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(LM)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0), .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]),
                                    .b(prod), .y(y_l[32*gl +: 32]), .err(e1), .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf_q <= 1'b0; end else begin gov <= ov_r; lf_q <= |lfl; end
    end else begin : g_lg
        // enables one cycle earlier (task at local ML) in the shell; the leaf's pin flops hold them at local 2 + ML
        localparam integer NG = W / LG;
        (* keep = "true" *) reg [W-1:0] lvs, sss;
        reg ov_r;
        wire [NVW-1:0] nv_p = cd[ML][DW-3 -: NVW];
        always @(posedge clk) for (integer l = 0; l < W; l = l + 1) begin
            lvs[l] <= cv[ML] && (l < nv_p);
            sss[l] <= cd[ML][DW-2];
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
        wire [NG-1:0] lfg;
        for (genvar gg = 0; gg < NG; gg = gg + 1) begin : g_grp
            // hard child: instantiated WITHOUT parameter overrides (its defaults are the hardened configuration)
            ot_hdc_v41x_hcp_lanes__d4g_hcbt u_lg (.clk(clk), .rst_n(rst_n), .fst(first), .gov_i(ov_r), .lv_i(lvs[gg*LG +: LG]),
                .ss_i(sss[gg*LG +: LG]), .w_i(w_data[gg*LG*32 +: LG*32]), .x_i(x_data[gg*LG*16 +: LG*16]),
                .s_i(sum_in[gg*LG*32 +: LG*32]), .y(sum_out[gg*LG*32 +: LG*32]), .lf(lfg[gg]));
        end
        // the leaves' registered group faults stand in for lf_q (same cycle)
        assign lf_any = |lfg;
    end endgenerate
endmodule

// el1011-hbm-hcvm/hc round 4: HARD LANE-GROUP LEAF of the systolic HC bank tile (ot_hdc_v41x_hcp_stage__d4g_hcbt LG = 8).  G FP32
// MAC lanes (product = w * x, partial chunk sum + product) exactly as the stage's flat g_lane, with its own clock tree.
// Every input lands in a pin flop that is the flat stage's input register (w_in, x_in, sum_q, lv_r, ss_r, gov, fst_q),
// every output is a flop (the seam register so_q when SOR, the adder output otherwise; lf = the flat lf_q), so the
// stage latency is bit-for-bit and cycle-for-cycle the flat one.  The defaults ARE the hardened configuration (the
// stage instantiates it without overrides).
module ot_hdc_v41x_hcp_lanes__d4g_hcbt #(
    parameter integer G     = 8,
    parameter integer LM    = 8,
    parameter integer LA    = 7,
    parameter integer SOR   = 1,
    parameter integer LRST  = 1,
    parameter integer ADRST = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            fst,
    input  wire            gov_i,
    input  wire [G-1:0]    lv_i,
    input  wire [G-1:0]    ss_i,
    input  wire [G*32-1:0] w_i,
    input  wire [G*16-1:0] x_i,
    input  wire [G*32-1:0] s_i,
    output wire [G*32-1:0] y,
    output reg             lf
);
    reg [G*32-1:0] w_in, sum_q; reg [G*16-1:0] x_in;
    (* keep = "true" *) reg [G-1:0] lv_r, ss_r;
    reg fst_q, gov;
    always @(posedge clk) begin
        w_in <= w_i; x_in <= x_i; sum_q <= s_i; lv_r <= lv_i; ss_r <= ss_i; fst_q <= fst;
    end
    wire [G-1:0] lfl;
    wire [G*32-1:0] y_l;
    generate if (SOR != 0) begin : g_sor
        reg [G*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign y = so_q;
    end else begin : g_nsor
        assign y = y_l;
    end endgenerate
    genvar gl;
    generate for (gl = 0; gl < G; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat__d4g_hcbt #(.LAT(LM)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat__d4g_hcbt #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0),
                                    .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]), .b(prod), .y(y_l[32*gl +: 32]), .err(e1),
                                    .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf <= 1'b0; end else begin gov <= gov_i; lf <= |lfl; end
endmodule


// Scoped source: rtl/lib/ot_rst_relay.sv
`timescale 1ns/1ps
// Registered, replicated local reset relay (synchronous-release reset tree).
//
// Design standard (coordinator 2026-10-10, drive-1010): a block's rst_n INPUT PORT drives only this relay.  The port net
// fans out to SYNC_STAGES synchronizer flops plus the asynchronous clear of the REGIONS*TREE_STAGES relay flops (assert
// stays asynchronous and immediate); release is synchronous and takes SYNC_STAGES + TREE_STAGES rising clk edges.
// Each region k then resets its own flops from rst_n[k], a flop output that placement can put next to that region, so no
// net from the port (or from one relay flop) spans the block.  On ~7 blocks the port -> thousands of reset flops net was
// the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen tile_e, ds qelem x1b).
//
// The region copies are logically identical, so synthesis would merge them: they are (* keep *) registers, which the
// ORFS flow's SYNTH_CANONICALIZE_TCL hook (physical/common_flow/ot_keep_regs.tcl, 0d3958d56) turns into kept flop cells.
//
// Consumers: release is delayed by RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES cycles (exactness is transaction-level; any
// logic that counts cycles from reset release must count from rst_n[k], never from the port).
module ot_rst_relay__d4g_hcbt #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay__d4g_hcbt: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay__d4g_hcbt: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay__d4g_hcbt: REGIONS must be >= 1");
    end
`endif
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 SQUARE ROOT for the V4.1 decode core: II 1, fixed
// DEPTH 31.  A stage-rebalanced copy of the qualified
// rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv (FRAC_SHIFT 15), with the decode
// core's port convention (v/a -> y/vo/fault).
//
// WHAT CHANGED, AND WHY.  The qualified pipe routes at 766 MHz on ASAP7: its
// critical path is the single finishing stage, which finds the root's leading
// bit by a priority encoder over all 28 root bits, shifts by a variable amount,
// rounds and encodes in one cycle.  But the leading bit is not variable: the
// radicand is a 24- or 25-bit significand times 2^(2*FRAC_SHIFT), so the root
// lies in [2^(11.5+F), 2^(12.5+F)) and its top bit is bit F+12 or bit F+11.
// Here the finish is a 2-way select on root[F+12] (stage 1: truncated
// significand, guard, sticky, exponent) and a separate round-and-encode
// (stage 2).  The digit recurrence and the decode stage are transcribed
// unchanged.  rtl/test/tb_hdc_fsqrt_equiv.sv drives both modules from one
// stimulus and requires the same code and the same refusal for every operand,
// one cycle later.
//
// FUNCTION.  y = RN_even(sqrt(a)); sqrt(+-0) = +0; subnormal arguments are
// normalised; a negative or nonfinite argument FAILS CLOSED (fault, y = +0).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt__d4g_hcbt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;   // the root's possible top bit

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (as qualified) ------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage (as qualified) --------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire take = (shifted >= trial);
            always @(posedge clk) begin
                rem_stage[g]  <= take ? (shifted - trial) : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1 -------------------------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;       // unbiased exponent before the rounding carry
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
            f_unb    <= $signed(TOP) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
            f_unb    <= $signed(TOP - 1) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end
    end

    // ---- finish 2: round to nearest even, encode --------------------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [24:0] rounded  = {1'b0, f_trunc} + {24'd0, round_up};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fsqrt_c12__d4g_hcbt: the 1.2 GHz (0.833 ns ASAP7 SS) successor of rtl/hdc/v41/ot_hdc_fsqrt__d4g_hcbt.sv for the HBM SU
// (hbm-su closure, 2026-10-05).  Same ports, same DEPTH 31, the same {vo, y, fault} on every cycle, bit for bit
// (rtl/test/tb_hdc_fsqrt_c12_equiv.sv drives both from one stimulus).  New file; the original is unchanged.
// Timing-only rewrites (closure kit: kept prefix adders, precomputed carries), no register moved:
//   * digit stage: `shifted >= trial` and `shifted - trial` are ONE kept Kogge-Stone subtractor
//     (ot_hdc_ksadd_k__d4g_hcbt: shifted + ~trial + 1; its carry out is the take bit), instead of a behavioural compare and
//     subtract that ABC ripples (routed -114 ps in the SU side pipe);
//   * finish 1 also registers both candidate biased exponents (no rounding carry / carry) and their
//     out-of-range flags, from the stage's own half exponent and top-bit select;
//   * finish 2 is only the kept 24-bit rounding increment (ot_hdc_inc_k__d4g_hcbt) and a carry select (was -167 ps).
//     When the increment carries out, the rounded significand is 2^24, so the 23 stored fraction bits are the
//     increment's low 23 bits either way.
// Needs rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k__d4g_hcbt, ot_hdc_inc_k__d4g_hcbt) and ot_hdc_vline (rtl/hdc/ot_hdc_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt_c12__d4g_hcbt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (unchanged) ----------------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage, one kept subtractor -------------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire [REM_W-1:0] diff;
            wire             take;      // carry out of shifted + ~trial + 1  ==  (shifted >= trial)
            ot_hdc_ksadd_k__d4g_hcbt #(.W(REM_W)) u_sub (.a(shifted), .b(~trial), .cin(1'b1), .s(diff), .cout(take));
            always @(posedge clk) begin
                rem_stage[g]  <= take ? diff : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1; both candidate exponents ------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    // biased = f_unb + 127 (+1 on a rounding carry); f_unb = half + (TOP - FRAC_SHIFT) (hi) or one less
    wire signed [EXP_W-1:0] h = half_stage[STAGES];
    wire signed [EXP_W-1:0] b_lo_hi = h + $signed(TOP - FRAC_SHIFT + 127);      // hi, no carry
    wire signed [EXP_W-1:0] b_lo_lo = h + $signed(TOP - 1 - FRAC_SHIFT + 127);  // lo, no carry
    wire signed [EXP_W-1:0] b_hi_hi = h + $signed(TOP - FRAC_SHIFT + 128);      // hi, carry
    wire [EXP_W-1:0] b0 = hi ? b_lo_hi : b_lo_lo;
    wire [EXP_W-1:0] b1 = hi ? b_hi_hi : b_lo_hi;                                 // lo + carry == hi, no carry
    reg [22:0] f_trunc_l;   // the truncated significand, low 23 bits
    reg        f_trunc23;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg [7:0]  f_b0, f_b1;
    reg        f_oor0, f_oor1;
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        f_b0 <= b0[7:0];
        f_b1 <= b1[7:0];
        f_oor0 <= ($signed(b0) < 12'sd1) || ($signed(b0) > 12'sd254);
        f_oor1 <= ($signed(b1) < 12'sd1) || ($signed(b1) > 12'sd254);
        if (hi) begin
            {f_trunc23, f_trunc_l} <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
        end else begin
            {f_trunc23, f_trunc_l} <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
        end
    end

    // ---- finish 2: kept rounding increment, carry select, encode --------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc_l[0]);
    wire [23:0] rounded;
    wire        carried;
    ot_hdc_inc_k__d4g_hcbt #(.W(24)) u_inc (.a({f_trunc23, f_trunc_l}), .inc(round_up), .y(rounded), .co(carried));
    wire [7:0] biased = carried ? f_b1 : f_b0;
    wire       out_of_range = carried ? f_oor1 : f_oor0;
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased, rounded[22:0]}; fault <= 1'b0; end
    end
endmodule

