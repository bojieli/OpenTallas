// QC-A0 10-23 (tools/qwen_romleaf/a0core/gen_a0c.py): the A0 planned hard core of the Qwen compute die plan,
// ONE clock entry.  Body = rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_romleaf_rr.sv unchanged; its 38 former clock-entry ports are
// internal nets of the core clock `ck` (one spine tap per planned core, COORD 10-23 07:24).  Same instance
// names, same logic, same cycles.
`timescale 1ns/1ps
// Local ROM-pair clock roots: each raw ROM shares a root with its capture and
// complete expansion/return pipeline. RQR north/south each has a compact root.
// Pure clock rewiring around the unchanged rp2_45 body: zero added edges.
// Q-ROMPARENT 10-16 21:00 (_rr): REGROOT 1 adds four regional roots: ck_rsw/ck_rnw = west-column halves of the RQR
// group words (east halves stay on ck_rs/ck_rn), ck_dw/ck_de = west/east halves of mq_wrom + s2_w. Zero added edges.
// Q-ROMPARENT 10-16 18:40: the eight TX roots ck_tx0..7 are separate compensated entries again (gate3 measured the
// shared ck root at TT 556..1230 ps over 10,644 sinks); each TX root owns only its LSL's two rungs + reset relay.
module qfd_tile_nk_a0c #(
    parameter integer G4_ROOTS = 1,
    parameter integer REGROOT_MODE = 3,
    // DIE-QC-16 ICG (opt-in, default 0 = the ungated form above, unchanged elaboration): 1 = one tile-root ICG
    // (ICGx8DC, QC-PG-4) gating every body clock entry except the input faces (ck_fa4 tap/tile_id/reset sample, ck_fa0/ck_fa1 n_a/n_b).
    // Enable from existing signals with a 1-cycle lead (see g_icg).  ICG_GOH = go hold cycles (go face -> engine idle
    // falls), ICG_DRAIN = cycles kept after the last activity (engine drained -> output faces, reset relays).
    parameter integer ICG = 0,   // 2 = B-hop (per-entry gates, relayed enables), see ICG_K_*
    parameter integer ICG_GOH = 3,
    // DIE-QC-33 (COORD 10-29, opt-in, default 0 = unchanged): > 0 -> the ICG enable state (dr, B-hop h[*], act's reset
    // term) resets from one ot_rst_relay (async assert, sync release after 2 + ICG_RRST edges) instead of raw rst_n, so
    // the rst_n port drives only the relay + the native reset sample.  Only the gates' open window grows (adds edges).
    parameter integer ICG_RRST = 0,
    parameter integer ICG_DRAIN = 64,
    // DIE-QC-58B (opt-in, default 0 = unchanged): ICG = 1 only.  1 = the root gate ENA is a registered enable en_q
    // beside the gate OR the go / node face copies (TT ENA setup: the gate CLK sits ~40 ps from ck while the enable
    // state launched at the full leaf insertion through ~400 um of cone); same gated edges as the combinational form.
    parameter integer ICG_EREG = 0,
    // DIE-QC-58B form (1) (opt-in, default 0 = unchanged): ICG = 1 and ICG_EREG = 1 only.  1 = the first stage after the
    // input faces (u_g IREG go_q / go_cp / ib_q / xl_q, node-port mis_q / fy_q) and the node leaf u_node (n-port first
    // stage) run on the ungated ck, so every gated capture is >= 2 edges after its face and ENA = en_q alone (the go /
    // node face terms reach the gate through en_q, one edge earlier; no face-launched combinational path to ENA).
    parameter integer ICG_IREG = 0,
    // QC-A0-KITS-13 B-hop (ICG = 2, COORD ruling d): one ot_a0_icg_hop gate per clock entry; its enable = the tile en
    // relayed through ICG_K_* ungated hops (bound K <= s - 1, s = measured gated depth of the entry from the ungated
    // faces: ck 1, rp 3, rsw/rnw/dw/de/rqr 4, tx 5, lsl 7, fa2 5 (NL) / 1 (NK), fa3 1, node 1).
    parameter integer ICG_K_CK = 0,
    parameter integer ICG_K_RP = 2,
    parameter integer ICG_K_RQ = 2,
    parameter integer ICG_K_TX = 2,
    parameter integer ICG_K_LSL = 2,
    parameter integer ICG_K_FA2 = 0,
    parameter integer ICG_K_FA3 = 0,
    parameter integer ICG_K_NODE = 0,
    // NKP (DIE-QC-66 11-03, opt-in, default 0 = unchanged): ot_qwen_w12_matvec_part logic-depth cuts (bit0 K-limit
    // prep, bit1 raw XTX rung 0 + per-leaf round, bit2 round-step sum); 0 visible cycles (see the engine)
    parameter integer NKP = 0,
    // LQR (QC-A0C-B5 11-06 vB, opt-in, default 0 = unchanged): bit0 romleaf r_q capture register (+1 ROM cycle),
    // bit1 per-leaf request register (+1 ROM cycle), bit2 node t_d register (+1 t_out pin cycle)
    parameter integer PINC = 0, // tools/qwen_romleaf/a0core/lqr/pinc_patch.py
    parameter integer RSTP = 0, parameter integer LQR = 0,
    // ICG_IDLE_RT (DIE-QC-66 11-03, opt-in, default 0 = unchanged; ICG = 1 + ICG_EREG = 1 only): me_idle re-timed
    // at the tile root on the ungated ck (idle_r) before the enable cone; absorbed by the dr drain (see g_erx)
    parameter integer ICG_IDLE_RT = 0
`ifndef SYNTHESIS
  , parameter integer ROM_TILE = -1
`endif
) (
    input  wire          ck,
`ifdef OT_A0_CK_TAPS
    // QC-P5 10-23 (COORD A0 clock, R4 revised, sink-count rule): 19 more taps of the SAME die clock, interior M7
    // pins where the die spine drops (20 taps, ~2.2k sinks each).  No RTL loads: the kit
    // (tools/qwen_romleaf/a0core/a0_clock_taps.tcl) moves each sink of ck to its nearest tap before CTS, so each tap
    // drives one local tree.
    input  wire          ck_t1,
    input  wire          ck_t2,
    input  wire          ck_t3,
    input  wire          ck_t4,
    input  wire          ck_t5,
    input  wire          ck_t6,
    input  wire          ck_t7,
    input  wire          ck_t8,
    input  wire          ck_t9,
    input  wire          ck_t10,
    input  wire          ck_t11,
    input  wire          ck_t12,
    input  wire          ck_t13,
    input  wire          ck_t14,
    input  wire          ck_t15,
    input  wire          ck_t16,
    input  wire          ck_t17,
    input  wire          ck_t18,
    input  wire          ck_t19,
`ifdef OT_A0_CK_TAPS24
    input  wire          ck_t20,
    input  wire          ck_t21,
    input  wire          ck_t22,
    input  wire          ck_t23,
`ifdef OT_A0_CK_TAPS31
    // QC-P6-A0 10-23 A0 v6: sink-anchored taps (gen_a0c6_taps.py; NL 31 taps, NK 32 with OT_A0_CK_TAPS32).  No RTL loads.
    input  wire          ck_t24,
    input  wire          ck_t25,
    input  wire          ck_t26,
    input  wire          ck_t27,
    input  wire          ck_t28,
    input  wire          ck_t29,
    input  wire          ck_t30,
`ifdef OT_A0_CK_TAPS32
    input  wire          ck_t31,
`ifdef OT_A0_CK_TAPS37
    // QC-A0 10-24 A0 v7: R4 grid (2 x 3 at 400 um) + the v6 sink taps as additions (gen_a0c7_taps.py; NL 37 taps,
    // NK 38 with OT_A0_CK_TAPS38).  No RTL loads.
    input  wire          ck_t32,
    input  wire          ck_t33,
    input  wire          ck_t34,
    input  wire          ck_t35,
    input  wire          ck_t36,
`ifdef OT_A0_CK_TAPS38
    input  wire          ck_t37,
`ifdef OT_A0_CK_TAPS42
    // QC-A0 10-24 A0 v8 (F1): hub tap additions (gen_a0c8_taps.py; NK ck_t38..ck_t41 with OT_A0_CK_TAPS42 on top of
    // OT_A0_CK_TAPS38, NL ck_t37..ck_t40 with OT_A0_CK_TAPS41 instead of OT_A0_CK_TAPS38).  No RTL loads.
    input  wire          ck_t38,
    input  wire          ck_t39,
    input  wire          ck_t40,
    input  wire          ck_t41,
`endif
`endif
`endif
`endif
`endif
`endif
`endif
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    output wire          tie_hi,
    output wire          tie_lo,
    input  wire [507:0]  tap,
    output wire [513:0]  t_out,
    input  wire [513:0]  n_a,
    input  wire [513:0]  n_b,
    output wire [513:0]  n_y
);
    // ---- DIE-QC-16 tile-root clock gate ------------------------------------------------------------------------
    // Gated body clock ck_g; the input faces (and the enable state below) stay on the ungated ck.  The ICG latches en
    // on the low phase, so en computed in cycle c (after edge c) clocks edge c+1:
    //   go face copy go_f = tap_q[0] (edge t)  -> clocks edge t+1, the first gated capture (IREG go_q)       [1-cycle lead]
    //   go hold go_h (ICG_GOH cycles)          -> covers go_q -> engine accept until the engine idle register falls
    //   ~me_idle (engine drained flag, ot_qwen_w12_matvec_part.idle via body port u_g.me_idle: OR of every valid stage)
    //   node face valid / fault bits           -> node pipe, mis_q, fy_q
    //   ~rst_n                                 -> clocked through reset
    //   drain counter dr (reloaded on any term, also during reset) -> output faces, tree/node drain, reset relays
    // former clock entries: one clock domain, CTS balances every sink (macros via clock_tree_path)
    wire ck_rp0;
    wire ck_rp1;
    wire ck_rp2;
    wire ck_rp3;
    wire ck_rp4;
    wire ck_rp5;
    wire ck_rp6;
    wire ck_rp7;
    wire ck_rp8;
    wire ck_rp9;
    wire ck_tx0;
    wire ck_tx1;
    wire ck_tx2;
    wire ck_tx3;
    wire ck_tx4;
    wire ck_tx5;
    wire ck_tx6;
    wire ck_tx7;
    wire ck_rsw;
    wire ck_rnw;
    wire ck_dw;
    wire ck_de;
    wire ck_rs;
    wire ck_rn;
    wire ck_fa0 = ck;
    wire ck_fa1 = ck;
    wire ck_fa2;
    wire ck_fa3;
    wire ck_fa4 = ck;
    wire ck_lsl0;
    wire ck_lsl1;
    wire ck_lsl2;
    wire ck_lsl3;
    wire ck_lsl4;
    wire ck_lsl5;
    wire ck_lsl6;
    wire ck_lsl7;
    wire ck_node;

    wire ck_g;
    wire ck_ireg;   // ICG_IREG: the u_g first-stage clock (ungated ck); unused (IRCK 0) otherwise
    wire me_idle;   // body port: the matvec engine idle register (QC-PG-5: threaded through the 4 body modules)
    generate if (ICG == 0) begin : g_noicg
        assign ck_g = ck;
        assign ck_rp0 = ck_g;
        assign ck_rp1 = ck_g;
        assign ck_rp2 = ck_g;
        assign ck_rp3 = ck_g;
        assign ck_rp4 = ck_g;
        assign ck_rp5 = ck_g;
        assign ck_rp6 = ck_g;
        assign ck_rp7 = ck_g;
        assign ck_rp8 = ck_g;
        assign ck_rp9 = ck_g;
        assign ck_tx0 = ck_g;
        assign ck_tx1 = ck_g;
        assign ck_tx2 = ck_g;
        assign ck_tx3 = ck_g;
        assign ck_tx4 = ck_g;
        assign ck_tx5 = ck_g;
        assign ck_tx6 = ck_g;
        assign ck_tx7 = ck_g;
        assign ck_rsw = ck_g;
        assign ck_rnw = ck_g;
        assign ck_dw = ck_g;
        assign ck_de = ck_g;
        assign ck_rs = ck_g;
        assign ck_rn = ck_g;
        assign ck_fa2 = ck_g;
        assign ck_fa3 = ck_g;
        assign ck_lsl0 = ck_g;
        assign ck_lsl1 = ck_g;
        assign ck_lsl2 = ck_g;
        assign ck_lsl3 = ck_g;
        assign ck_lsl4 = ck_g;
        assign ck_lsl5 = ck_g;
        assign ck_lsl6 = ck_g;
        assign ck_lsl7 = ck_g;
        assign ck_node = ck_g;
        assign ck_ireg = ck_g;
    end else begin : g_icg
`ifdef SYNTHESIS
        localparam integer mut = 0;
`else
        integer mut;                                             // bench-only mutants (+ICG_MUT=n, 0 = none)
        initial begin mut = 0; if ($value$plusargs("ICG_MUT=%d", mut)) begin end end
`endif
        (* keep = 1 *) reg go_f;
        reg [ICG_GOH-1:0] go_h;
        always @(posedge ck) begin go_f <= tap[0]; go_h <= {go_h[ICG_GOH-2:0], go_f}; end
        // node face activity: n_a/n_b valid (mis_q, node pipe) and fault bits (fy_q), from copies of the n_a_q/n_b_q faces
        reg [3:0] nv_f;
        always @(posedge ck) nv_f <= {n_b[513], n_a[513], n_b[512], n_a[512]};
        // PINC: body inputs n_a_c / n_b_c lag the n_a_q / n_b_q faces one edge, so the activity term lags with them (nv_f2).
        // nv_f shares its flops with the late face; nv_f2 is the retimed copy the ICG enable reads, tapped early (OT_B3_MID).
        // Async reset keeps it a distinct cell from n_a_p / n_b_p, which have the same D.
        reg [3:0] nv_f2;
`ifdef OT_PINC_MUT
        reg [3:0] nv_f3;
        wire nv_act = (PINC == 0) ? |nv_f : ((`OT_PINC_MUT == 3) ? |nv_f3 : |nv_f2);
`else
        wire nv_act = (PINC == 0) ? |nv_f : |nv_f2;
`endif
        // me_idle = engine drained flag from the body port (u_g.me_idle = u_me.idle, registered, 1 in reset)
        wire go_act = ((mut == 1) ? 1'b0 : go_f) | ((mut == 6) ? 1'b0 : |go_h);
        wire rst_icg;
        if (ICG_RRST == 0) begin : g_rr0
            assign rst_icg = rst_n;
        end else begin : g_rr
            wire [0:0] rr;
            ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(ICG_RRST)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
            assign rst_icg = rr[0];
        end
`ifndef SYNTHESIS
        // bench mutant 11: release one edge early (relay depth k - 1); mutant 10: hop tx3 left on raw rst_n
        reg [7:0] rr_m1;
        always @(posedge ck or negedge rst_n) if (!rst_n) rr_m1 <= 8'd0; else rr_m1 <= {rr_m1[6:0], 1'b1};
        wire rst_e = (mut == 11 && ICG_RRST > 0) ? rr_m1[ICG_RRST] : rst_icg;
`else
        wire rst_e = rst_icg;
`endif
        always @(posedge ck or negedge rst_e) if (!rst_e) nv_f2 <= 4'd0; else nv_f2 <= nv_f;
`ifdef OT_PINC_MUT
        always @(posedge ck) nv_f3 <= nv_f2;
`endif
        wire act = ((mut == 5) ? 1'b0 : !rst_e) | go_act | ((mut == 2) ? 1'b0 : !me_idle) | ((mut == 4) ? 1'b0 : nv_act);
        reg [7:0] dr;
        always @(posedge ck or negedge rst_e)
            if (!rst_e) dr <= (mut == 5) ? 8'd0 : 8'(ICG_DRAIN);
            else if (act) dr <= 8'(ICG_DRAIN);
            else if (dr != 8'd0) dr <= dr - 8'd1;
        wire en = act | ((mut == 3) ? 1'b0 : (dr != 8'd0)) | (mut == 9);
        if (ICG == 1) begin : g_root   // DIE-QC-16: one tile-root gate
            wire en_g;
            if (ICG_EREG == 0) begin : g_ec
                assign en_g = en;
            end else if (ICG_IDLE_RT == 0) begin : g_er
                // en_q after edge t = en after edge t-1, async-set while rst_e is low (as dr), so it covers every
                // term of en(t) that is state at t-1 (go_h, dr, the reset relay, !me_idle: the body only changes
                // me_idle on an edge it was clocked by, i.e. en(t-1) = 1).  The terms that are port values at edge t
                // stay combinational from their face flops (go_f, node face copies nv_f); no new port load
                // (face_guard: one face flop per input bit).  ENA = en_q | go_f [| nv_act]; bench mutant 12 drops go_f.
                reg en_q;
                always @(posedge ck or negedge rst_e) if (!rst_e) en_q <= 1'b1; else en_q <= en;
                // ICG_IREG: ENA = en_q only (go_f / nv_act enter en, hence en_q, one edge before the first gated
                // capture of their face); bench mutant 13 puts the first stage back on ck_g, 14 the node leaf.
                assign en_g = en_q | ((ICG_IREG != 0) ? 1'b0 : (((mut == 12) ? 1'b0 : go_f) | ((mut == 4) ? 1'b0 : nv_act)));
            end else begin : g_erx
                // ICG_IDLE_RT: me_idle (u_me.idle, far side of the tile) re-timed here on the ungated ck; act / dr / en
                // as above but from idle_r (the outer act / dr / en are then unused).  !idle_r lags !me_idle by one
                // edge: a reload by the lagged term alone loads ICG_DRAIN - 1, so dr_x / en_x match dr / en on every
                // edge (the busy start lies inside the go_h / dr window of its go).  Bench: tb_a0_nkp MUT4 idle_r
                // stuck idle, MUT5 dr_x stuck 0, MUT6 (+ICG_MUT=16) lagged reload = ICG_DRAIN must FAIL.
                reg idle_r;
                always @(posedge ck or negedge rst_e) if (!rst_e) idle_r <= 1'b1; else idle_r <= me_idle;
                wire act_o = ((mut == 5) ? 1'b0 : !rst_e) | go_act | ((mut == 4) ? 1'b0 : nv_act);   // terms not lagged
                wire busy_r = (mut == 2) ? 1'b0 : !idle_r;                                              // lagged !me_idle
                wire act_x = act_o | busy_r;
                reg [7:0] dr_x;
                always @(posedge ck or negedge rst_e)
                    if (!rst_e) dr_x <= (mut == 5) ? 8'd0 : 8'(ICG_DRAIN);
                    else if (act_o) dr_x <= 8'(ICG_DRAIN);
                    else if (busy_r) dr_x <= 8'(ICG_DRAIN - ((mut == 16) ? 0 : 1));   // = original reload one edge earlier
                    else if (dr_x != 8'd0) dr_x <= dr_x - 8'd1;
                wire en_x = act_x | ((mut == 3) ? 1'b0 : (dr_x != 8'd0)) | (mut == 9);
                reg en_q;
                always @(posedge ck or negedge rst_e) if (!rst_e) en_q <= 1'b1; else en_q <= en_x;
                assign en_g = en_q | ((ICG_IREG != 0) ? 1'b0 : (((mut == 12) ? 1'b0 : go_f) | ((mut == 4) ? 1'b0 : nv_act)));
            end
`ifdef SYNTHESIS
            ICGx8DC_ASAP7_75t_R u_icg (.CLK(ck), .ENA(en_g), .SE(1'b0), .GCLK(ck_g));
`else
            reg en_l;
            /* verilator lint_off COMBDLY */
            always_latch if (!ck) en_l = en_g;    // ICG cell function: latch transparent while ck is low, AND with ck
            /* verilator lint_on COMBDLY */
            assign ck_g = ck & en_l;
`endif
            assign ck_rp0 = ck_g;
            assign ck_rp1 = ck_g;
            assign ck_rp2 = ck_g;
            assign ck_rp3 = ck_g;
            assign ck_rp4 = ck_g;
            assign ck_rp5 = ck_g;
            assign ck_rp6 = ck_g;
            assign ck_rp7 = ck_g;
            assign ck_rp8 = ck_g;
            assign ck_rp9 = ck_g;
            assign ck_tx0 = ck_g;
            assign ck_tx1 = ck_g;
            assign ck_tx2 = ck_g;
            assign ck_tx3 = ck_g;
            assign ck_tx4 = ck_g;
            assign ck_tx5 = ck_g;
            assign ck_tx6 = ck_g;
            assign ck_tx7 = ck_g;
            assign ck_rsw = ck_g;
            assign ck_rnw = ck_g;
            assign ck_dw = ck_g;
            assign ck_de = ck_g;
            assign ck_rs = ck_g;
            assign ck_rn = ck_g;
            assign ck_fa2 = ck_g;
            assign ck_fa3 = ck_g;
            assign ck_lsl0 = ck_g;
            assign ck_lsl1 = ck_g;
            assign ck_lsl2 = ck_g;
            assign ck_lsl3 = ck_g;
            assign ck_lsl4 = ck_g;
            assign ck_lsl5 = ck_g;
            assign ck_lsl6 = ck_g;
            assign ck_lsl7 = ck_g;
            assign ck_node = (ICG_IREG != 0 && mut != 14) ? ck : ck_g;
            assign ck_ireg = (ICG_IREG != 0 && mut != 13) ? ck : ck_g;
        end else begin : g_hop         // QC-A0-KITS-13 B-hop: one gate per clock entry, relayed enable
            wire xk_all = (mut == 7);  // bench mutant: every hop one stage longer (ck K 0 -> 1 > s - 1 = 0)
            wire xk_rp = (mut == 8);   // bench mutant: ROM-pair hops one stage longer (K 2 -> 3 > s - 1 = 2)
            assign ck_ireg = ck_g;
            ot_a0_icg_hop #(.K(ICG_K_CK)) u_hop_ck (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_g));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp0 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp0));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp1 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp1));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp2 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp2));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp3 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp3));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp4 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp4));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp5 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp5));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp6 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp6));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp7 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp7));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp8 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp8));
            ot_a0_icg_hop #(.K(ICG_K_RP)) u_hop_rp9 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all | xk_rp), .gck(ck_rp9));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx0 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx0));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx1 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx1));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx2 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx2));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx3 (.ck(ck), .rst_n((mut == 10) ? rst_n : rst_e), .en(en), .xk(xk_all), .gck(ck_tx3));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx4 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx4));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx5 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx5));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx6 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx6));
            ot_a0_icg_hop #(.K(ICG_K_TX)) u_hop_tx7 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_tx7));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_rsw (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_rsw));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_rnw (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_rnw));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_dw (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_dw));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_de (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_de));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_rs (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_rs));
            ot_a0_icg_hop #(.K(ICG_K_RQ)) u_hop_rn (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_rn));
            ot_a0_icg_hop #(.K(ICG_K_FA2)) u_hop_fa2 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_fa2));
            ot_a0_icg_hop #(.K(ICG_K_FA3)) u_hop_fa3 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_fa3));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl0 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl0));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl1 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl1));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl2 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl2));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl3 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl3));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl4 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl4));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl5 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl5));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl6 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl6));
            ot_a0_icg_hop #(.K(ICG_K_LSL)) u_hop_lsl7 (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_lsl7));
            ot_a0_icg_hop #(.K(ICG_K_NODE)) u_hop_node (.ck(ck), .rst_n(rst_e), .en(en), .xk(xk_all), .gck(ck_node));
        end
        initial if (ICG_GOH < 2 || ICG_DRAIN < 1 || ICG_DRAIN > 255 || ICG > 2) $fatal(1, "a0c ICG: ICG <= 2, ICG_GOH >= 2, 1 <= ICG_DRAIN <= 255");
        initial if (ICG_IREG != 0 && (ICG != 1 || ICG_EREG == 0)) $fatal(1, "a0c ICG_IREG needs ICG = 1 and ICG_EREG = 1");
    end endgenerate
`ifndef SYNTHESIS
    qfd_tile_nk_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE),.IRCK((ICG == 1 && ICG_IREG != 0) ? 1 : 0),.NKP(NKP), .LQR(LQR), .RSTP(RSTP), .PINC(PINC)) u_g (
`else
    qfd_tile_nk_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE),.IRCK((ICG == 1 && ICG_IREG != 0) ? 1 : 0),.NKP(NKP), .LQR(LQR), .RSTP(RSTP), .PINC(PINC)) u_g (
`endif
        .ck(ck_g),
        .me_idle(me_idle),
        .ck_rp0(ck_rp0),
        .ck_rp1(ck_rp1),
        .ck_rp2(ck_rp2),
        .ck_rp3(ck_rp3),
        .ck_rp4(ck_rp4),
        .ck_rp5(ck_rp5),
        .ck_rp6(ck_rp6),
        .ck_rp7(ck_rp7),
        .ck_rp8(ck_rp8),
        .ck_rp9(ck_rp9),
        .ck_rom0(ck_rp0),
        .ck_rom1(ck_rp1),
        .ck_rom2(ck_rp2),
        .ck_rom3(ck_rp3),
        .ck_rom4(ck_rp4),
        .ck_rom5(ck_rp5),
        .ck_rom6(ck_rp6),
        .ck_rom7(ck_rp7),
        .ck_rom8(ck_rp8),
        .ck_rom9(ck_rp9),
        .ck_tx0(ck_tx0),
        .ck_tx1(ck_tx1),
        .ck_tx2(ck_tx2),
        .ck_tx3(ck_tx3),
        .ck_tx4(ck_tx4),
        .ck_tx5(ck_tx5),
        .ck_tx6(ck_tx6),
        .ck_tx7(ck_tx7),
        .ck_rsw(ck_rsw),
        .ck_rnw(ck_rnw),
        .ck_dw(ck_dw),
        .ck_de(ck_de),
        .ck_rqr0(ck_rs),
        .ck_rqr1(ck_rn),
        .ck_fa0(ck_fa0),
        .ck_fa1(ck_fa1),
        .ck_fa2(ck_fa2),
        .ck_fa3(ck_fa3),
        .ck_fa4(ck_fa4),
        .ck_lsl0(ck_lsl0),
        .ck_lsl1(ck_lsl1),
        .ck_lsl2(ck_lsl2),
        .ck_lsl3(ck_lsl3),
        .ck_lsl4(ck_lsl4),
        .ck_lsl5(ck_lsl5),
        .ck_lsl6(ck_lsl6),
        .ck_lsl7(ck_lsl7),
        .ck_node(ck_node),
        .ck_ireg(ck_ireg),
        .rst_n(rst_n),
        .tile_id(tile_id),
        .tie_hi(tie_hi),
        .tie_lo(tie_lo),
        .tap(tap),
        .t_out(t_out),
        .n_a(n_a),
        .n_b(n_b),
        .n_y(n_y)
    );
    generate if (ICG_IDLE_RT != 0) begin : g_irt_chk
        initial if (ICG != 1 || ICG_EREG == 0 || ICG_DRAIN < 2) $fatal(1, "ICG_IDLE_RT needs ICG = 1, ICG_EREG = 1, ICG_DRAIN >= 2");
    end endgenerate
endmodule
