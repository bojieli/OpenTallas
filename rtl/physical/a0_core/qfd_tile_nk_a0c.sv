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
    parameter integer ICG = 0,
    parameter integer ICG_GOH = 3,
    parameter integer ICG_DRAIN = 64
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
    wire ck_g;
    wire me_idle;   // body port: the matvec engine idle register (QC-PG-5: threaded through the 4 body modules)
    generate if (ICG == 0) begin : g_noicg
        assign ck_g = ck;
    end else begin : g_icg
`ifdef SYNTHESIS
        localparam integer mut = 0;
`else
        integer mut;                                             // bench-only mutants (+ICG_MUT=n, 0 = none)
        initial begin mut = 0; if ($value$plusargs("ICG_MUT=%d", mut)) begin end end
`endif
        reg go_f;
        reg [ICG_GOH-1:0] go_h;
        always @(posedge ck) begin go_f <= tap[0]; go_h <= {go_h[ICG_GOH-2:0], go_f}; end
        // node face activity: n_a/n_b valid (mis_q, node pipe) and fault bits (fy_q), from copies of the n_a_q/n_b_q faces
        reg [3:0] nv_f;
        always @(posedge ck) nv_f <= {n_b[513], n_a[513], n_b[512], n_a[512]};
        wire nv_act = |nv_f;
        // me_idle = engine drained flag from the body port (u_g.me_idle = u_me.idle, registered, 1 in reset)
        wire go_act = ((mut == 1) ? 1'b0 : go_f) | ((mut == 6) ? 1'b0 : |go_h);
        wire act = ((mut == 5) ? 1'b0 : !rst_n) | go_act | ((mut == 2) ? 1'b0 : !me_idle) | ((mut == 4) ? 1'b0 : nv_act);
        reg [7:0] dr;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) dr <= (mut == 5) ? 8'd0 : 8'(ICG_DRAIN);
            else if (act) dr <= 8'(ICG_DRAIN);
            else if (dr != 8'd0) dr <= dr - 8'd1;
        wire en = act | ((mut == 3) ? 1'b0 : (dr != 8'd0)) | (mut == 9);
`ifdef SYNTHESIS
        ICGx8DC_ASAP7_75t_R u_icg (.CLK(ck), .ENA(en), .SE(1'b0), .GCLK(ck_g));
`else
        reg en_l;
        /* verilator lint_off COMBDLY */
        always_latch if (!ck) en_l = en;      // ICG cell function: latch transparent while ck is low, AND with ck
        /* verilator lint_on COMBDLY */
        assign ck_g = ck & en_l;
`endif
        initial if (ICG_GOH < 2 || ICG_DRAIN < 1 || ICG_DRAIN > 255) $fatal(1, "a0c ICG: ICG_GOH >= 2, 1 <= ICG_DRAIN <= 255");
    end endgenerate
    // former clock entries: one clock domain, CTS balances every sink (macros via clock_tree_path)
    wire ck_rp0 = ck_g;
    wire ck_rp1 = ck_g;
    wire ck_rp2 = ck_g;
    wire ck_rp3 = ck_g;
    wire ck_rp4 = ck_g;
    wire ck_rp5 = ck_g;
    wire ck_rp6 = ck_g;
    wire ck_rp7 = ck_g;
    wire ck_rp8 = ck_g;
    wire ck_rp9 = ck_g;
    wire ck_tx0 = ck_g;
    wire ck_tx1 = ck_g;
    wire ck_tx2 = ck_g;
    wire ck_tx3 = ck_g;
    wire ck_tx4 = ck_g;
    wire ck_tx5 = ck_g;
    wire ck_tx6 = ck_g;
    wire ck_tx7 = ck_g;
    wire ck_rsw = ck_g;
    wire ck_rnw = ck_g;
    wire ck_dw = ck_g;
    wire ck_de = ck_g;
    wire ck_rs = ck_g;
    wire ck_rn = ck_g;
    wire ck_fa0 = ck;
    wire ck_fa1 = ck;
    wire ck_fa2 = ck_g;
    wire ck_fa3 = ck_g;
    wire ck_fa4 = ck;
    wire ck_lsl0 = ck_g;
    wire ck_lsl1 = ck_g;
    wire ck_lsl2 = ck_g;
    wire ck_lsl3 = ck_g;
    wire ck_lsl4 = ck_g;
    wire ck_lsl5 = ck_g;
    wire ck_lsl6 = ck_g;
    wire ck_lsl7 = ck_g;
    wire ck_node = ck_g;
`ifndef SYNTHESIS
    qfd_tile_nk_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
`else
    qfd_tile_nk_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
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
endmodule
