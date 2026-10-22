`timescale 1ns/1ps
// S81-SAFE-FIX/CTRL 10-19: dual-clock Gray-pointer FIFO with a GROUPED, REPLICATED read side, for dsfd_ctrl_rg2.
// Same write side, pointers, credits, overflow and reset behaviour as ot_s81ph_afifo (that module is unchanged: the
// closed S81-PH dsfd_ctrl_pc view binds it).  What changes is the read side (safe-design checklist item 3, fanout):
//   ot_s81ph_afifo: r_d = mem[rbin] -- the 3-bit binary read pointer selects every one of the W bits (W x 7 mux2 loads
//   on three flops), and the reader's pop (from the PHY's k_rdy) fans into it.
//   here: the word is split into NG = ceil(W / G) column groups of G (= 32) bits.  Each group has its OWN kept one-hot
//   read select rsel[g] (DEPTH flops) and its own kept empty copy, rotated by its own pop input r_pop_g[g]; the group's
//   read word is the AND-OR of rsel[g] with its 32-bit slice of the rows.  Every select flop drives G AND gates (<= 32
//   loads) and every pop copy drives one group (DEPTH + 1 flops).  r_pop_g must equal r_pop bit for bit (the caller
//   drives them from replicated copies of the same registered state); the master rbin / rgray / empty are unchanged.
// All copies are declared (* keep *): physical/common_flow/ot_keep_regs.tcl puts keep on the driving flip-flops so
// opt_merge cannot fold them back (memory yosys-keep-parameterised-modules-1018: kept by attribute, not module name).
`default_nettype none
module ot_s81ph_afifo_g #(
    parameter integer W = 32,
    parameter integer DEPTH = 8,
    parameter integer AF = 2,
    parameter integer G = 32
) (
    input  wire         wclk,
    input  wire         wrst_n,
    input  wire         w_v,
    input  wire [W-1:0] w_d,
    output reg          w_rdy,      // registered: >= AF entries free
    output reg          w_credit,   // registered pulse: one entry freed by the reader
    output reg          w_ovf,      // sticky: a write into a full FIFO (dropped)
    input  wire         rclk,
    input  wire         rrst_n,
    output wire         r_v,
    input  wire         r_pop,
    input  wire [(W+G-1)/G-1:0] r_pop_g,   // per-group copies of r_pop (equal values, separate drivers)
    output wire [W-1:0] r_d
);
    localparam integer AW = $clog2(DEPTH);
    localparam integer PW = AW + 1;
    localparam integer NG = (W + G - 1) / G;
    function automatic [PW-1:0] g2b(input [PW-1:0] g);
        integer i;
        begin
            g2b[PW-1] = g[PW-1];
            for (i = PW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i];
        end
    endfunction
    // ---- write side: identical to ot_s81ph_afifo (registered one-hot row enables, one per 64-bit slice)
    localparam integer NCP = (W + 63) / 64;
    wire [DEPTH*W-1:0] mrd;
    reg [PW-1:0] wbin, wgray, rbin, rgray, cbin;
    (* async_reg = "true" *) reg [PW-1:0] rg_w1, rg_w2;
    (* async_reg = "true" *) reg [PW-1:0] wg_r1, wg_r2;
    wire [PW-1:0] rbin_w = g2b(rg_w2);
    wire [PW-1:0] used = wbin - rbin_w;
    wire          full = used[AW];
    wire          wfire = w_v && !full;
    wire [PW-1:0] wbin_n = wbin + {{(PW-1){1'b0}}, wfire};
    wire [PW-1:0] used_n = wbin_n - rbin_w;
    wire [PW-1:0] used_nn = wbin_n - g2b(rg_w1);
    wire          full_n = used_nn[AW];
    genvar ge, gc, gg;
    generate for (ge = 0; ge < DEPTH; ge = ge + 1) begin : g_e
        for (gc = 0; gc < NCP; gc = gc + 1) begin : g_c
            localparam integer LO = gc * 64;
            localparam integer WD = (gc == NCP - 1) ? W - LO : 64;
            reg [WD-1:0] q;
            (* keep *) reg wen_q;
            always @(posedge wclk or negedge wrst_n)
                if (!wrst_n) wen_q <= (ge == 0);
                else wen_q <= (wbin_n[AW-1:0] == ge) && !full_n;
            always @(posedge wclk) if (wen_q) q <= w_d[LO +: WD];
            assign mrd[ge*W + LO +: WD] = q;
        end
    end endgenerate
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; cbin <= 0;
            w_rdy <= 1'b0; w_credit <= 1'b0; w_ovf <= 1'b0;
        end else begin
            wbin <= wbin_n;
            wgray <= (wbin_n >> 1) ^ wbin_n;
            rg_w1 <= rgray; rg_w2 <= rg_w1;
            w_rdy <= (DEPTH - 32'(used_n)) >= AF;
            w_credit <= cbin != rbin_w;
            if (cbin != rbin_w) cbin <= cbin + 1'b1;
            if (w_v && full) w_ovf <= 1'b1;
        end
    // ---- read side master (pointer, Gray pointer, empty): as ot_s81ph_afifo
    reg empty;
    wire rfire = r_pop && !empty;
    wire [PW-1:0] rbin_n = rbin + {{(PW-1){1'b0}}, rfire};
    wire [PW-1:0] rgray_n = (rbin_n >> 1) ^ rbin_n;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; empty <= 1'b1;
        end else begin
            rbin <= rbin_n; rgray <= rgray_n;
            wg_r1 <= wgray; wg_r2 <= wg_r1;
            empty <= rgray_n == wg_r2;
        end
    assign r_v = !empty;
    // ---- read side copies: per group a kept empty copy and a kept one-hot select, rotated on the group's own pop.
    // empty_c[g] follows `empty` exactly: its next value needs the group's rbin_n, rebuilt from the group's one-hot
    // (rsel rotated by the group's fire) -- no master net crosses into the group except wg_r2 (PW flops, NG loads each).
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_rd
        localparam integer LO = gg * G;
        localparam integer WG = (gg == NG - 1) ? W - LO : G;
        (* keep *) reg [DEPTH-1:0] rsel;     // one-hot rbin[AW-1:0]
        (* keep *) reg             emp;      // copy of empty
        (* keep *) reg             rwrap;    // copy of rbin[AW] (the Gray compare needs the wrap bit)
        wire fire_g = r_pop_g[gg] && !emp;
        wire [DEPTH-1:0] rsel_n = fire_g ? {rsel[DEPTH-2:0], rsel[DEPTH-1]} : rsel;
        wire             rwrap_n = rwrap ^ (fire_g && rsel[DEPTH-1]);
        reg  [AW-1:0]    rlo_n;
        integer k;
        always @(*) begin
            rlo_n = {AW{1'b0}};
            for (k = 0; k < DEPTH; k = k + 1) if (rsel_n[k]) rlo_n = rlo_n | k[AW-1:0];
        end
        wire [PW-1:0] rb_n = {rwrap_n, rlo_n};
        wire [PW-1:0] rg_n = (rb_n >> 1) ^ rb_n;
        always @(posedge rclk or negedge rrst_n)
            if (!rrst_n) begin rsel <= {{(DEPTH-1){1'b0}}, 1'b1}; emp <= 1'b1; rwrap <= 1'b0; end
            else begin rsel <= rsel_n; rwrap <= rwrap_n; emp <= rg_n == wg_r2; end
        // AND-OR read of the group slice: rsel[e] gates row e's WG bits (each select flop -> WG <= 32 AND gates)
        reg [WG-1:0] rdg;
        integer e;
        always @(*) begin
            rdg = {WG{1'b0}};
            for (e = 0; e < DEPTH; e = e + 1) rdg = rdg | (mrd[e*W + LO +: WG] & {WG{rsel[e]}});
        end
        assign r_d[LO +: WG] = rdg;
    end endgenerate
endmodule
`default_nettype wire
