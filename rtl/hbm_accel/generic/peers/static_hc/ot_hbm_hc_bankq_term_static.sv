`timescale 1ns/1ps
`default_nettype none
// LH-UNREAD / F-T 2026-10-19: TERMINAL plain ring bank of the HC quarter engine (ring position 7, the chain's LAST bank).
// ot_hbm_hc_bankq_static forwards the chain descriptor (o_v, o_ss, o_nv, o_wa, o_xa; 29 b) to the next bank. Bank 7
// has no next bank: its sum_out/f_out go to bank 0's chain-exit relay (s_i) and nothing reads the descriptor, so the die
// carried 4 x 29 = 116 driven-but-unread bits (held unread class terminal_chain_control). This master is the terminal
// variant: the forward-descriptor PORTS and their CPO face registers do not exist. Everything else is cycle-exact with
// ot_hbm_hc_bankq_static #(CPI, CPO): beat landing, BF16 residual check (wfault), CPI chain landing, the bank stage
// (ot_hbm_hc_bank_static, unchanged), and the CPO registers of sum_out / f_out. Canonical sources stay unchanged.
// The inner bank stage still has its o_* outputs; inside this tile they have no load (stage chain flops sit in the
// hard lane leaves, so they stay inside the leaf; no die-level bit exists any more).
// SAFE-DESIGN checklist (owner 10-19):
//  1 Pins: every input lands in a flop (CPI=1 descriptor/sum/f; beat/write pins as the canonical bank), every remaining
//    output is a flop (CPO=1 sum_out/f_out; wfault sticky flop); reset enters ot_rst_relay (registered release). PASS
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
module ot_hbm_hc_bankq_term_core #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    input  wire          clk, rst_n, first,
    input  wire          d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, j, input wire [9:0] wa,
    output reg           wfault
);
    wire [0:0] rc;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rc));
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
    ot_hbm_hc_bank_static #(.W(64), .AW(10), .LM(8), .LA(7), .MUT(MUT == 1 ? 1 : 0), .RST_RELAY(1)) u_b (
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
    ot_hbm_hc_bankq_term_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (.clk(clk), .rst_n(rst_n), .first(1'b0),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
        .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
endmodule
`default_nettype wire
