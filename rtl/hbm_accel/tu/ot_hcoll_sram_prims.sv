`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SRAM-backed primitives of the switched-tier collective endpoint (stream hbm-coll-rtl, 2026-10-08).
// They replace the HA2 flop primitives inside ot_hbm_accel_tu_endpoint_sr (the hfd_coll die view):
//   ot_ha2_delay (circular buffer, D-way x W read mux, D x W flops)  -> ot_hcoll_sdelay (SRAM, fixed read offset)
//                                                                       or ot_hcoll_shdelay (plain shift line)
//   ot_ha2_fifo  (2^AW x W flops + 2^AW-way read mux)                 -> ot_hcoll_sfifo (SRAM + 4-entry flop head)
// Storage is the ASAP7 1R1W macro ot_sram_1r1w_128x256_m1_r2c2 (the one hfd_vm uses: physical/asap7_memory_macros),
// NB = ceil(W / 256) macros side by side.  Design rules (REDESIGN_RULES): the word reaching a macro comes from a flop
// (input pin flop, no logic between it and the macro), every macro output is captured in a flop with no logic before
// it, and the head a consumer sees is a flop.
// ---------------------------------------------------------------------------

// NB macros of 128 x 256 as one 128 x (256 NB) array (unused high bits tied off)
module ot_hcoll_sram128 #(parameter integer W = 545) (
    input  wire         clk,
    input  wire         r_ce,
    input  wire [6:0]   r_addr,
    output wire [W-1:0] rd,
    input  wire         w_ce,
    input  wire [6:0]   w_addr,
    input  wire [W-1:0] wd
);
    localparam integer NB = (W + 255) / 256;
    wire [NB*256-1:0] q;
    wire [NB*256-1:0] d = {{(NB*256-W){1'b0}}, wd};
    for (genvar m = 0; m < NB; m = m + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_sram (.clk(clk), .r_ce_in(r_ce), .r_addr_in(r_addr), .rd_out(q[m*256 +: 256]),
            .w_ce_in(w_ce), .w_addr_in(w_addr), .wd_in(d[m*256 +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end
    assign rd = q[W-1:0];
endmodule

// Fixed-latency delay line in SRAM: same port list and the same latency D as ot_ha2_delay, exact on valid beats
// (d_out is defined only while v_out).  v_in at cycle t -> d_p (input flop, edge t) -> macro write (edge t+1, address
// cnt) -> macro read at the fixed offset cnt - (D-3) (edge t+D-2) -> capture flop q (edge t+D-1) -> d_out at t+D.
// Valid travels a D-flop shift line; the macro is only enabled on valid beats.  4 <= D <= 130.
module ot_hcoll_sdelay #(
    parameter integer W = 1,
    parameter integer D = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
`ifndef SYNTHESIS
    initial if (D < 4 || D - 3 >= 128) $fatal(1, "ot_hcoll_sdelay: D=%0d out of range 4..130", D);
`endif
    reg [D-1:0] vs;
    reg [6:0]   cnt;
    reg [W-1:0] d_p, q;
    wire [W-1:0] rd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vs <= '0; cnt <= 7'd0; end
        else begin vs <= {vs[D-2:0], v_in}; cnt <= cnt + 7'd1; end
    always @(posedge clk) begin d_p <= d_in; q <= rd; end
    ot_hcoll_sram128 #(.W(W)) u_m (.clk(clk), .r_ce(vs[D-3]), .r_addr(cnt - 7'(D - 3)), .rd(rd),
        .w_ce(vs[0]), .w_addr(cnt), .wd(d_p));
    assign v_out = vs[D-1];
    assign d_out = q;
endmodule

// Plain shift-register delay (no read mux) for short / narrow lines; same ports and latency as ot_ha2_delay.
module ot_hcoll_shdelay #(
    parameter integer W = 1,
    parameter integer D = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    reg [D-1:0] vs;
    reg [W-1:0] ds [0:D-1];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vs <= '0;
        else vs <= {vs[D-2:0], v_in};
    always @(posedge clk) begin
        ds[0] <= d_in;
        for (integer i = 1; i < D; i = i + 1) ds[i] <= ds[i-1];
    end
    assign v_out = vs[D-1];
    assign d_out = ds[D-1];
endmodule

// SRAM FIFO with a first-word-fall-through flop head; the port list of ot_ha2_fifo (push/din/pop/empty/dout/ovf/count).
//   write: push, din -> pin flops push_p / din_p -> macro write (no logic between the flops and the macro)
//   read : a fixed pipeline that never stalls, gated by a local credit (ocr = free head slots, K):
//          fetch (r_ce) -> rd (macro) -> raw_q (capture flop, no logic before it) -> head FIFO (K flops, ot_ha2_fifo)
//   pop  : pops the head FIFO (as ot_ha2_fifo: pop && !empty) and returns its credit the same edge.
// Capacity 2^AW (SRAM) + K (head); overflow (a push_p while the SRAM part is full) is sticky in ovf.
// AW = 8: two 128-deep banks (bank = address MSB, one read and one write a cycle, either bank), each captured in its
// own flop; the bank select is applied after the capture flops, in front of the head FIFO.
// Latency push -> head visible: 5 edges (ot_ha2_fifo: 1).  K = 4 covers the 4-edge credit loop: full rate.
module ot_hcoll_sfifo #(
    parameter integer W  = 8,
    parameter integer AW = 7,
    parameter integer K  = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire         empty,
    output wire [W-1:0] dout,
    output reg          ovf,
    output wire [AW:0]  count
);
`ifndef SYNTHESIS
    initial if (AW > 8 || AW < 1 || K != 4) $fatal(1, "ot_hcoll_sfifo: AW=%0d (1..8), K=%0d (4)", AW, K);
`endif
    localparam integer N = 1 << AW;
    localparam integer NBK = (AW > 7) ? 2 : 1;
    reg          push_p;
    reg [W-1:0]  din_p;
    reg [W-1:0]  rawb [0:NBK-1];
    wire [W-1:0] rdb [0:NBK-1];
    reg          bs1, bs2;
    reg [AW:0]   scnt;
    reg [AW-1:0] wp, rp;
    reg [2:0]    ocr;
    reg          v1, v2;
    wire full  = scnt == (AW+1)'(N);
    wire put   = push_p && !full;
    wire fetch = (scnt != '0) && (ocr != 3'd0);
    wire hovf;
    wire [2:0] hc;
    wire do_pop = pop && !empty;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            push_p <= 1'b0; scnt <= '0; wp <= '0; rp <= '0; ocr <= 3'(K); v1 <= 1'b0; v2 <= 1'b0; ovf <= 1'b0;
        end else begin
            push_p <= push;
            scnt <= scnt + (AW+1)'(put) - (AW+1)'(fetch);
            if (put) wp <= wp + 1'b1;
            if (fetch) rp <= rp + 1'b1;
            ocr <= ocr - 3'(fetch) + 3'(do_pop);
            v1 <= fetch; v2 <= v1;
            if ((push_p && full) || hovf) ovf <= 1'b1;
        end
    always @(posedge clk) begin
        din_p <= din;
        for (integer b = 0; b < NBK; b = b + 1) rawb[b] <= rdb[b];
        bs1 <= (NBK > 1) ? rp[AW-1] : 1'b0; bs2 <= bs1;
    end
    for (genvar b = 0; b < NBK; b = b + 1) begin : g_bk
        ot_hcoll_sram128 #(.W(W)) u_m (.clk(clk), .r_ce(fetch && (NBK == 1 || rp[AW-1] == 1'(b))), .r_addr(7'(rp)),
            .rd(rdb[b]), .w_ce(put && (NBK == 1 || wp[AW-1] == 1'(b))), .w_addr(7'(wp)), .wd(din_p));
    end
    wire [W-1:0] raw_q = rawb[(NBK > 1) ? bs2 : 1'b0];
    ot_ha2_fifo #(.W(W), .AW(2)) u_head (.clk(clk), .rst_n(rst_n), .push(v2), .din(raw_q), .pop(pop),
        .empty(empty), .dout(dout), .ovf(hovf), .count(hc));
    assign count = scnt;
endmodule

// SRAM FIFO with an EXPORTED head (per-port split, 2026-10-08): ot_hcoll_sfifo whose head FIFO lives across a hard-
// macro boundary.  out_v / out_d leave an output flop (one beat per fetched word, in order); cr_in is a REGISTERED
// credit-return pulse (one per freed consumer head slot, K consumer slots).  The loop fetch -> rd -> capture -> out
// flop -> consumer in flop -> consumer head -> pop -> consumer credit flop -> cr_in flop -> ocr is 8 edges: K = 8.
module ot_hcoll_sfifo_x #(
    parameter integer W  = 8,
    parameter integer AW = 7,
    parameter integer K  = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         cr_in,
    output reg          out_v,
    output reg  [W-1:0] out_d,
    output reg          ovf
);
`ifndef SYNTHESIS
    initial if (AW > 8 || AW < 1 || K < 1 || K > 15) $fatal(1, "ot_hcoll_sfifo_x: AW=%0d (1..8), K=%0d (1..15)", AW, K);
`endif
    localparam integer N = 1 << AW;
    localparam integer NBK = (AW > 7) ? 2 : 1;
    reg          push_p;
    reg [W-1:0]  din_p;
    reg [W-1:0]  rawb [0:NBK-1];
    wire [W-1:0] rdb [0:NBK-1];
    reg          bs1, bs2;
    reg [AW:0]   scnt;
    reg [AW-1:0] wp, rp;
    reg [3:0]    ocr;
    reg          v1, v2;
    wire full  = scnt == (AW+1)'(N);
    wire put   = push_p && !full;
    wire fetch = (scnt != '0) && (ocr != 4'd0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            push_p <= 1'b0; scnt <= '0; wp <= '0; rp <= '0; ocr <= 4'(K); v1 <= 1'b0; v2 <= 1'b0; ovf <= 1'b0; out_v <= 1'b0;
        end else begin
            push_p <= push;
            scnt <= scnt + (AW+1)'(put) - (AW+1)'(fetch);
            if (put) wp <= wp + 1'b1;
            if (fetch) rp <= rp + 1'b1;
            ocr <= ocr - 4'(fetch) + 4'(cr_in);
            v1 <= fetch; v2 <= v1; out_v <= v2;
            if (push_p && full) ovf <= 1'b1;
        end
    always @(posedge clk) begin
        din_p <= din;
        for (integer b = 0; b < NBK; b = b + 1) rawb[b] <= rdb[b];
        bs1 <= (NBK > 1) ? rp[AW-1] : 1'b0; bs2 <= bs1;
        out_d <= rawb[(NBK > 1) ? bs2 : 1'b0];
    end
    for (genvar b = 0; b < NBK; b = b + 1) begin : g_bk
        ot_hcoll_sram128 #(.W(W)) u_m (.clk(clk), .r_ce(fetch && (NBK == 1 || rp[AW-1] == 1'(b))), .r_addr(7'(rp)),
            .rd(rdb[b]), .w_ce(put && (NBK == 1 || wp[AW-1] == 1'(b))), .w_addr(7'(wp)), .wd(din_p));
    end
endmodule
