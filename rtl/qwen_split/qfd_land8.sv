`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// QW-LAND8 (2026-10-19, LEAD-QW 12:15 decision: Q.STA.LAND600.3 = the 8-slot D8 landing; contract 5a266752c
// setup age >= 1.25 T, read -> next-overwrite retention >= 3.875 T, 60/25 ps + 150/100 ps cross-root reserves unchanged;
// storage = the D8 hybrid MODEL dee8d6b3a "direct FF pointer ring" class for small lanes: W <= 32 here, < 2 kb state).
//
// ot_qfd_land8: landing with the hop-0 role (FIRST = 1, the qfd_landh0 frame: written on the SOURCE root ck_s, read on
// the RECEIVING root ck).  Differences to ot_qfd_land (qfd_fwd_lane.sv, D4):
//   * D = 8 slots, wc / rc modulo 16 (4 bits), FOUR K strap pins k[3:0] (K = 0 means 16: warm after 16 read edges).
//   * The hop-0 ICG enable is a REGISTER: en (pin, the source's released reset) -> en_s0 (face flop, async clear by en)
//     -> en_icg (kept flop, async clear by en_s0) -> ICG.ENA.  Nothing combinational reaches the gate enable: the ICG
//     enable pin is driven by exactly one flop Q (no AND / OR terms).  Assert is immediate (async clear chain, works with
//     every clock stopped); release takes two ck_s edges (G + 1, G + 2), the first gated write edge is G + 3.
//   * Write state (one-hot write select, slot valid) and read state (one-hot read select, warm) are KEPT per 16-bit
//     region copies (<= 16 data loads per select flop, <= 32 everywhere); the write epoch copies en_q[r] and the
//     receiver reset copies rs1[r] are second stages of ONE face flop each (en_s0 / rs0), so every copy releases on the
//     same edge as the top-level counters.
//   * No ready, credit, occupancy or stall: both pointers free-run (owner static-schedule rule 10-14).  Read selects are
//     registered one-hot (decoded one edge early from rc + 1 - K); the cross-root path is bank flop -> 8:1 AND-OR -> o.
//   * ICG = 0 (fallback variant): no clock gate at all, the ring write clock is ck_s itself; the en copies hold the write
//     state cleared (async) until G + 2, so the calendar is identical to ICG = 1 (bank 0 is rewritten during reset with
//     its valid bit clear; the first valid write is still edge G + 3).
// CALENDAR (the die strap; checked exactly by tools/qwen_split/bench_land8.sh):
//   source word w(e) launched on source edge e is written on ck_s edge e + 1 into slot (e - G - 2) mod 8, epoch
//   (e - G - 2) mod 16; G = the source edge after which en is 1.  Receiver: rs is 1 after receiver edge R0, rc counts
//   from edge R0 + 3 (rc = t - R0 - 3 before edge t).  o after receiver edge t holds w(t - L) for
//   K = (L + G - R0 - 1) mod 16,
//   where L is the receiver-edge latency the die chooses so that the write -> read age (L - 1) T + phi lies in the
//   D8 window [1.25 T, 4.125 T] (phi = receiver root phase behind the source root at the landing).  Words with
//   e < G + 2 (never written in this epoch) read as 0 bubbles; output is 0 until warm (K read edges after release).
// FAULT (assertion only): after warm, a VALID read slot whose stored epoch is not rc - K sets the sticky fault.
// Bench mutants (tools/qwen_split/bench_land8.sh): OT_QFD_LAND8_MUT_{SEL,NAIVE,VLD,ENCOMB,K3,WSEL,RSEL}.
// ---------------------------------------------------------------------------------------------------------------------

(* keep_hierarchy = "yes" *)
module ot_qfd_land8_gate (input wire ck, input wire en, output wire gclk);
    ot_hdc_cg u_cg (.clk(ck), .en(en), .gclk(gclk));
endmodule

// one kept region: write half on wck, read half on ck.  W <= 16 data bits; META = 1 stores the 4-bit epochs instead.
(* keep_hierarchy = "yes" *)
module ot_qfd_land8_region #(parameter integer W = 16) (
    input  wire         wck,        // ring write clock (gated ck_s, or ck_s for ICG = 0)
    input  wire         ckw,        // ungated ck_s (the en copy is clocked here, as the ICG enable)
    input  wire         en_s0,      // source-side first en stage (async clear of the en copy)
    input  wire [W-1:0] i,
    input  wire         ck,         // receiving root
    input  wire         rs0,        // receiver-side first reset stage
    input  wire [2:0]   rnext,      // (rc + 1 - K) mod 8, from the top's registered rc / k_q
    input  wire [2:0]   rseed,      // (0 - K) mod 8
    input  wire         warm_next,
    output wire [7:0]   vld_o,
    output wire [7:0]   rdsel_o,
    output reg  [W-1:0] o
);
    // ---------------------------------------------------------------- write half
    (* keep = "true", dont_touch = "true" *) reg en_q;      // region copy of the write epoch (2nd en stage)
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_q = en_s0;                                // mutant: write epoch = the en pin (closed-view form)
`else
    always @(posedge ckw or negedge en_s0)
        if (!en_s0) en_q <= 1'b0; else en_q <= 1'b1;
`endif
    // one-hot write select, bit 0 stored inverted: the all-clear reset state selects slot 0
    (* keep = "true", dont_touch = "true" *) reg [7:0] wsq;
    wire [7:0] ws = {wsq[7:1], ~wsq[0]};
    always @(posedge wck or negedge en_q)
        if (!en_q) wsq <= 8'b0;
`ifdef OT_QFD_LAND8_MUT_WSEL
        else wsq <= {ws[5:0], ws[7], ~ws[6]};              // mutant: select skips a slot
`else
        else wsq <= {ws[6:0], ~ws[7]};                     // rotate left (stored form)
`endif
    (* keep = "true", dont_touch = "true" *) reg [7:0] vld;
    always @(posedge wck or negedge en_q)
        if (!en_q) vld <= 8'b0;
`ifdef OT_QFD_LAND8_MUT_VLD
        else vld <= 8'hff;                                  // mutant: every slot valid at once
`else
        else vld <= vld | ws;
`endif
    reg [W-1:0] b0, b1, b2, b3, b4, b5, b6, b7;
    always @(posedge wck) begin
        if (ws[0]) b0 <= i;
        if (ws[1]) b1 <= i;
        if (ws[2]) b2 <= i;
        if (ws[3]) b3 <= i;
        if (ws[4]) b4 <= i;
        if (ws[5]) b5 <= i;
        if (ws[6]) b6 <= i;
        if (ws[7]) b7 <= i;
    end
    // ---------------------------------------------------------------- read half
    (* keep = "true", dont_touch = "true" *) reg rs1, warm_q;
    always @(posedge ck or negedge rs0)
        if (!rs0) rs1 <= 1'b0; else rs1 <= 1'b1;
    always @(posedge ck or negedge rs1)
        if (!rs1) warm_q <= 1'b0; else warm_q <= warm_next;
    (* keep = "true", dont_touch = "true" *) reg [7:0] rdsel;
    wire [2:0] rsel_idx = rs1 ? rnext : rseed;
`ifdef OT_QFD_LAND8_MUT_RSEL
    always @(posedge ck) rdsel <= 8'b1 << (rsel_idx + 3'd2);     // mutant: read select two slots late
`else
    always @(posedge ck) rdsel <= 8'b1 << rsel_idx;
`endif
    wire [7:0] use_ = rdsel & vld & {8{warm_q}};
    assign vld_o = vld;
    assign rdsel_o = rdsel;
`ifdef OT_QFD_LAND8_MUT_NAIVE
    always @(posedge ck) o <= warm_q ? i : {W{1'b0}};          // mutant: retime register only, no ring
`else
    always @(posedge ck)
        o <= ({W{use_[0]}} & b0) | ({W{use_[1]}} & b1) | ({W{use_[2]}} & b2) | ({W{use_[3]}} & b3)
           | ({W{use_[4]}} & b4) | ({W{use_[5]}} & b5) | ({W{use_[6]}} & b6) | ({W{use_[7]}} & b7);
`endif
endmodule

module ot_qfd_land8 #(
    parameter integer W    = 32,
    parameter integer ICG  = 1       // 1: hop-0 clock gate on ck_s (registered enable); 0: no gate (fallback)
) (
    input  wire         ck_s,        // source block root (ring write side)
    input  wire         en,          // source released reset (active high)
    input  wire [W-1:0] i,
    input  wire         ck,          // receiving block root
    input  wire         rs,          // receiving block regional reset, active low
    input  wire [3:0]   k,           // K strap (four identity straps from the instance's own tie cells)
    output wire [W-1:0] o,
    output reg          fault
);
    localparam integer NR = (W + 15) / 16;
    // ---------------------------------------------------------------- source-side en landing (registered ICG enable)
    (* keep = "true", dont_touch = "true" *) reg en_s0;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_s0 = en;                                  // mutant: no en register at all (en -> gate / epoch)
`else
    always @(posedge ck_s or negedge en)
        if (!en) en_s0 <= 1'b0; else en_s0 <= 1'b1;
`endif
    (* keep = "true", dont_touch = "true" *) reg en_icg;    // the ONLY driver of the ICG enable pin
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_icg = en_s0;                              // mutant: en combinational into the gate (closed-view form)
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_icg <= 1'b0; else en_icg <= 1'b1;
`endif
    wire wck;
    generate if (ICG != 0) begin : g_icg
        ot_qfd_land8_gate u_fwd0 (.ck(ck_s), .en(en_icg), .gclk(wck));
    end else begin : g_nogate
        assign wck = ck_s;
    end endgenerate
    // write epoch counter (metadata only), its own en copy
    (* keep = "true", dont_touch = "true" *) reg en_qm;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_qm = en_s0;
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_qm <= 1'b0; else en_qm <= 1'b1;
`endif
    reg [3:0] wc;
    always @(posedge wck or negedge en_qm)
        if (!en_qm) wc <= 4'b0; else wc <= wc + 1'b1;
    // ---------------------------------------------------------------- receiver-side reset landing, counters
    (* keep = "true", dont_touch = "true" *) reg rs0, rs1;
    always @(posedge ck or negedge rs)
        if (!rs) rs0 <= 1'b0; else rs0 <= 1'b1;
    always @(posedge ck or negedge rs0)
        if (!rs0) rs1 <= 1'b0; else rs1 <= 1'b1;
    reg [3:0] k_q;
`ifdef OT_QFD_LAND8_MUT_K3
    always @(posedge ck) k_q <= {1'b0, k[2:0]};              // mutant: three-pin K silently zero-extended (D4 ABI)
`else
    always @(posedge ck) k_q <= k;
`endif
    reg [3:0] rc;
    reg warm;
    wire warm_next = warm | (rc == k_q - 1'b1);
    always @(posedge ck or negedge rs1)
        if (!rs1) begin rc <= 4'b0; warm <= 1'b0; end
        else begin rc <= rc + 1'b1; warm <= warm_next; end
`ifdef OT_QFD_LAND8_MUT_SEL
    wire [3:0] nxt = rc + 4'd2 - k_q;                        // mutant: read slot one late
    wire [3:0] seed = 4'd1 - k_q;
`else
    wire [3:0] nxt = rc + 4'd1 - k_q;
    wire [3:0] seed = 4'd0 - k_q;
`endif
    // ---------------------------------------------------------------- data regions + metadata region
    wire [W-1:0] o_r;
    assign o = o_r;
    genvar r;
    generate for (r = 0; r < NR; r = r + 1) begin : g_region
        localparam integer LO = r * 16, N = (W - LO < 16) ? W - LO : 16;
        wire [7:0] vld_u, rds_u;
        ot_qfd_land8_region #(.W(N)) u_region (
            .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(i[LO +: N]), .ck(ck), .rs0(rs0),
            .rnext(nxt[2:0]), .rseed(seed[2:0]), .warm_next(warm_next),
            .vld_o(vld_u), .rdsel_o(rds_u), .o(o_r[LO +: N]));
    end endgenerate
    // metadata: the write epoch of every slot, read through the region's own select into an aligned compare
    wire [7:0] vld_m, rds_m;
    wire [3:0] ep_o;
    ot_qfd_land8_region #(.W(4)) u_meta (
        .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(wc), .ck(ck), .rs0(rs0),
        .rnext(nxt[2:0]), .rseed(seed[2:0]), .warm_next(warm_next),
        .vld_o(vld_m), .rdsel_o(rds_m), .o(ep_o));
    reg [3:0] exp_d;
    reg chk_d;
    always @(posedge ck) begin exp_d <= rc - k_q; chk_d <= warm && |(rds_m & vld_m); end
    always @(posedge ck or negedge rs1)
        if (!rs1) fault <= 1'b0;
        else if (chk_d && ep_o != exp_d) fault <= 1'b1;
`ifndef SYNTHESIS
    initial if (W < 1 || W > 128) $fatal(1, "ot_qfd_land8: 1 <= W <= 128 (direct FF ring class; wider lanes -> SRAM record)");
`endif
endmodule
`default_nettype wire
