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
    parameter integer REGROOT_MODE = 3
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
`ifdef OT_A0_CK_TAPS53
    // PATH-QC-NK2 10-25 A0 v10 (NK R6): core-only taps at the LSL fp1 / bottom ROM-leaf clock pins (ck_t42..ck_t49)
    // + 3 re-pitch flop taps (ck_t50..ck_t52), gen_a0c10_core_clock.py.  No RTL loads.
    input  wire          ck_t42,
    input  wire          ck_t43,
    input  wire          ck_t44,
    input  wire          ck_t45,
    input  wire          ck_t46,
    input  wire          ck_t47,
    input  wire          ck_t48,
    input  wire          ck_t49,
    input  wire          ck_t50,
    input  wire          ck_t51,
    input  wire          ck_t52,
`endif
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
    // former clock entries: one clock domain, CTS balances every sink (macros via clock_tree_path)
    wire ck_rp0 = ck;
    wire ck_rp1 = ck;
    wire ck_rp2 = ck;
    wire ck_rp3 = ck;
    wire ck_rp4 = ck;
    wire ck_rp5 = ck;
    wire ck_rp6 = ck;
    wire ck_rp7 = ck;
    wire ck_rp8 = ck;
    wire ck_rp9 = ck;
    wire ck_tx0 = ck;
    wire ck_tx1 = ck;
    wire ck_tx2 = ck;
    wire ck_tx3 = ck;
    wire ck_tx4 = ck;
    wire ck_tx5 = ck;
    wire ck_tx6 = ck;
    wire ck_tx7 = ck;
    wire ck_rsw = ck;
    wire ck_rnw = ck;
    wire ck_dw = ck;
    wire ck_de = ck;
    wire ck_rs = ck;
    wire ck_rn = ck;
    wire ck_fa0 = ck;
    wire ck_fa1 = ck;
    wire ck_fa2 = ck;
    wire ck_fa3 = ck;
    wire ck_fa4 = ck;
    wire ck_lsl0 = ck;
    wire ck_lsl1 = ck;
    wire ck_lsl2 = ck;
    wire ck_lsl3 = ck;
    wire ck_lsl4 = ck;
    wire ck_lsl5 = ck;
    wire ck_lsl6 = ck;
    wire ck_lsl7 = ck;
    wire ck_node = ck;
`ifndef SYNTHESIS
    qfd_tile_nk_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
`else
    qfd_tile_nk_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
`endif
        .ck(ck),
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
