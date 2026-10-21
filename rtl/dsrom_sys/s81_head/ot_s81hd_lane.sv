`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HD-CTL (S81-HEAD 10-21): ot_s81hd_lane = the head-die lane block (SPEC results/arch/s81_head_1021/SPEC.md section 1):
// one dsfd_coll_lane_w_safe8_ntf (the closed-kit REACH 2 collective link lane, unchanged) + a STATIC core adapter.
// 13 instances on the head die: 6 TP4 mesh (rank argmax all-gather), 2 host (lk_HOST0/1), 5 draft fan-out.
//
// SerDes side: exactly as the end-slice lanes (ot_s81sl_slice_lepw_mab_mu_72 u_ln0..3):
//   rx [513:0] = {ot_pdie_serdes st[1:0] = {live, fault}, rx beat [511:0]}, re-ordered into the lane rx word
//                {fault, live, beat, valid}; valid = registered receive enable (1 from the cycle after reset release).
//   tx [511:0] = the lane's gearbox beat.  chb = static board-lane strap (lane timeout basis).
// Flow control lives ONLY here, at the off-die boundary (owner 10-14 / 10-21): the lane's core face is a CREDIT link
// (rtl/common/ot_link_credit.sv protocol: lo_r = one credit pulse per landing pop, CRED 8; li_r = one credit pulse per
// beat taken, the lane's sender holds CRED 8).  The core side of this block is VALID-ONLY:
//   TX  tx_v / tx_d [552:0] = one lane flit {last, data 552} a cycle at most.  It lands in a pin flop and is pushed into a
//       3-flit buffer (3 x 553 = 1,659 b < the 2 kb SRAM threshold: flops, one-hot pointers, no runtime-indexed array
//       above 2 kb); the buffer drains into the lane whenever a credit is in hand.  The static schedule keeps the
//       per-lane frame rate <= 1 per 2 cycles and bursts <= 3 frames (ctl TX spacing counters), so the buffer never
//       fills; a push into a full buffer is a sticky fault (flt[3]) and the flit is dropped (nothing overwritten).
//   RX  rx_v / rx_d [552:0] = every lane flit, from pin flops, one cycle after the lane presents it (always-accept: the
//       credit goes back the next cycle).  A beat arriving while the lane sender holds no credit (would-overflow:
//       protocol violation) is a sticky fault (flt[3]).
// Census (pre-gate native rules, <= 32 loads / driver): the TX buffer is BIT-SLICED into 35 kept-hierarchy slices of
// 16 bits (ot_s81hd_lane_txs, non-parameterised so Yosys keeps the instance names); tx_v / lo_r land in 2 kept pin-flop
// copies (ot_s81hd_kf, <= 18 slices each), and every slice carries its own replica of the buffer control (credit count,
// occupancy, one-hot pointers), so no control flop drives more than its slice (16 data bits; a mapped hold mux loads its
// select twice).  Slices stay in lock step (identical inputs); the bench
// checks it (OT_S81HD_LANE_CHK).
// Reset: rst_n -> ot_rst_relay_tree3 (root, group: the 2-stage landing; leaf: <= 32 reset pins each); only control /
// valid bits are reset (data unreset).
// Cycles (compiler-known, off-die elastic): tx_v pin -> lo_v 5 edges (pin copy, slice flop, buffer write, send flop) with a credit
// in hand; li_v -> rx_v 1 edge.  flt = {adapter fault, lane flt[2:0] = {meso, gearbox, endpoint}} from flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_lane (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          chb,
    input  wire [513:0]  rx,
    output wire [511:0]  tx,
    input  wire          tx_v,
    input  wire [552:0]  tx_d,
    output wire          rx_v,
    output wire [552:0]  rx_d,
    output wire [3:0]    flt
);
    localparam integer NS = 35;                 // 35 x 16 = 560 >= 553
    localparam integer NR = NS + 3;             // reset leaves: slices, lane, rx, misc
    wire [NR-1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(NR)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire r_lane = rr[NS], r_rx = rr[NS + 1], r_misc = rr[NS + 2];
    // ---- lane rx word and receive enable
    reg rxen;
    always @(posedge ck or negedge r_misc) if (!r_misc) rxen <= 1'b0; else rxen <= 1'b1;
    wire [514:0] lrx = {rx[512], rx[513], rx[511:0], rxen};
    // ---- the lane tile (closed kit dscoll_lane_w_s8n*)
    wire lo_v, lo_r, li_v, li_r; wire [552:0] lo_d, li_d; wire [2:0] lf;
    dsfd_coll_lane_w_safe8_ntf u_ln (.ck(ck), .rs(r_lane), .chb(chb), .rx(lrx), .tx(tx), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(lf));
    // ---- TX: bit-sliced 3-flit buffer, credit sender
    // pin stage: tx_d lands here, tx_v / lo_r land in 2 kept copies each (<= 18 slices per copy)
    reg [552:0] txd_p;
    always @(posedge ck) txd_p <= tx_d;
    wire [1:0] tv_c, cr_c;
    ot_s81hd_kf u_tv0 (.ck(ck), .d(tx_v), .q(tv_c[0])); ot_s81hd_kf u_tv1 (.ck(ck), .d(tx_v), .q(tv_c[1]));
    ot_s81hd_kf u_cr0 (.ck(ck), .d(lo_r), .q(cr_c[0])); ot_s81hd_kf u_cr1 (.ck(ck), .d(lo_r), .q(cr_c[1]));
    wire [NS*16-1:0] txd_w = {{(NS*16-553){1'b0}}, txd_p};
    wire [NS*16-1:0] lod_w;
    wire [NS-1:0] lov_s, ovf_s;
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_txs
        (* keep_hierarchy = "yes" *) ot_s81hd_lane_txs u_s (.ck(ck), .rn(rr[s]), .tv(tv_c[s % 2]), .td(txd_w[16*s +: 16]),
            .cr(cr_c[s % 2]), .lv(lov_s[s]), .ld(lod_w[16*s +: 16]), .ovf(ovf_s[s]));
    end endgenerate
    assign lo_v = lov_s[0];
    assign lo_d = lod_w[552:0];
`ifndef SYNTHESIS
`ifdef OT_S81HD_LANE_CHK
    always @(posedge ck) if (rr[0] && (lov_s != {NS{1'b0}}) && (lov_s != {NS{1'b1}})) $fatal(1, "ot_s81hd_lane: TX slices out of lock step");
`endif
`endif
    // ---- RX: always-accept pin flops, credit pulse per beat, would-overflow check against the sender's credits
    reg rv_q; reg [552:0] rd_q; reg cr_q; reg [3:0] snd; reg rx_f;
    always @(posedge ck) rd_q <= li_d;
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin rv_q <= 1'b0; cr_q <= 1'b0; snd <= 4'd8; rx_f <= 1'b0; end
        else begin
            rv_q <= li_v;
            cr_q <= li_v;                                    // the beat is taken now: credit back next edge
            snd <= snd - {3'd0, li_v} + {3'd0, cr_q};
            rx_f <= rx_f | (li_v && snd == 4'd0);
        end
    assign li_r = cr_q;
    assign rx_v = rv_q;
    assign rx_d = rd_q;
    // ---- faults
    reg [3:0] flt_q;
    always @(posedge ck or negedge r_misc) if (!r_misc) flt_q <= 4'd0; else flt_q <= {rx_f | ovf_s[0], lf};
    assign flt = flt_q;
endmodule

// One 16-bit slice of the lane TX buffer with its own replica of the control (kept hierarchy, no parameters).
(* keep_hierarchy = "yes" *) module ot_s81hd_lane_txs (
    input  wire        ck,
    input  wire        rn,
    input  wire        tv,          // tx_v pin (this slice's own pin flop)
    input  wire [15:0] td,
    input  wire        cr,          // lo_r credit pulse pin (own pin flop)
    output reg         lv,
    output reg  [15:0] ld,
    output reg         ovf
);
    (* keep = "true" *) reg tv_q, cr_q;
    reg [15:0] td_q;
    reg [15:0] q0, q1, q2;
    reg [2:0] wp, rp;               // one-hot
    reg [1:0] n;                    // occupancy 0..3
    reg [3:0] c;                    // credits in hand 0..8
    wire full = n == 2'd3;
    wire push = tv_q && !full;
    wire send = n != 2'd0 && c != 4'd0;
    always @(posedge ck) begin
        td_q <= td;
        if (push && wp[0]) q0 <= td_q;
        if (push && wp[1]) q1 <= td_q;
        if (push && wp[2]) q2 <= td_q;
        ld <= ({16{rp[0]}} & q0) | ({16{rp[1]}} & q1) | ({16{rp[2]}} & q2);   // loads every cycle (DFREE)
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin tv_q <= 1'b0; cr_q <= 1'b0; wp <= 3'b001; rp <= 3'b001; n <= 2'd0; c <= 4'd8; lv <= 1'b0; ovf <= 1'b0; end
        else begin
            tv_q <= tv; cr_q <= cr;
            if (push) wp <= {wp[1:0], wp[2]};
            if (send) rp <= {rp[1:0], rp[2]};
            n <= n + {1'b0, push} - {1'b0, send};
            c <= c + {3'd0, cr_q} - {3'd0, send};
            lv <= send;
            ovf <= ovf | (tv_q && full);
        end
endmodule
