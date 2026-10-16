`timescale 1ns/1ps
// Q-TILE45 r6 (2026-10-16): qfd_tile_nl_rp2_g3 = qfd_tile_nl_rp2_45 with its clock structure re-partitioned into 13 entries
// (was 41).  Pure clock wiring around the unchanged body: every register, ROM macro, LSL/node leaf,
// data edge and cycle is the body's; no logic is added.  Measured motive (E1 on the r5 placed ODB, results/arch/
// qwen_tile_repack_2115/r6_e1): the ROM capture (590 ps ROM clk->q) failed TT setup by up to 151 ps only because each
// ROM was its own die entry (150 ps cross-entry reserve against its capture root); one shared root per ROM group lets
// CTS balance the ROM clock pin with its capture/expansion/relay registers and the group OR register.
//   ck    : core control + all eight TX relay banks (10.6k sinks), compact at the core; TX -> LSL is the long hop
//   ck_rs : south bank group (banks 0..2: 6 ROM clock pins + their pair pipelines + RQR south, 14.2k sinks)
//   ck_rn : north bank group (banks 3..4: 4 ROM clock pins + pair pipelines + RQR north, 9.8k sinks)
//   ck_fa2, ck_fa4 : unchanged pin-anchored face roots; ck_lsl0..ck_lsl7 unchanged hard-child entries
module qfd_tile_nl_rp2_g3 #(
    parameter integer G3_ROOTS = 1
`ifndef SYNTHESIS
  , parameter integer ROM_TILE = -1
`endif
) (
    input  wire          ck,
    input  wire          ck_rs,
    input  wire          ck_rn,
    input  wire          ck_fa2,
    input  wire          ck_fa4,
    input  wire          ck_lsl0,
    input  wire          ck_lsl1,
    input  wire          ck_lsl2,
    input  wire          ck_lsl3,
    input  wire          ck_lsl4,
    input  wire          ck_lsl5,
    input  wire          ck_lsl6,
    input  wire          ck_lsl7,
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    output wire          tie_hi,
    output wire          tie_lo,
    input  wire [507:0]  tap,
    output wire [513:0]  t_out
);
`ifndef SYNTHESIS
    qfd_tile_nl_rp2_45 #(.ROM_TILE(ROM_TILE)) u_g (
`else
    qfd_tile_nl_rp2_45 u_g (
`endif
        .ck(ck),
        .ck_rp0(ck_rs),
        .ck_rp1(ck_rs),
        .ck_rp2(ck_rs),
        .ck_rp3(ck_rn),
        .ck_rp4(ck_rn),
        .ck_rp5(ck_rs),
        .ck_rp6(ck_rs),
        .ck_rp7(ck_rs),
        .ck_rp8(ck_rn),
        .ck_rp9(ck_rn),
        .ck_rom0(ck_rs),
        .ck_rom1(ck_rs),
        .ck_rom2(ck_rs),
        .ck_rom3(ck_rn),
        .ck_rom4(ck_rn),
        .ck_rom5(ck_rs),
        .ck_rom6(ck_rs),
        .ck_rom7(ck_rs),
        .ck_rom8(ck_rn),
        .ck_rom9(ck_rn),
        .ck_tx0(ck),
        .ck_tx1(ck),
        .ck_tx2(ck),
        .ck_tx3(ck),
        .ck_tx4(ck),
        .ck_tx5(ck),
        .ck_tx6(ck),
        .ck_tx7(ck),
        .ck_rqr0(ck_rs),
        .ck_rqr1(ck_rn),
        .ck_fa2(ck_fa2),
        .ck_fa4(ck_fa4),
        .ck_lsl0(ck_lsl0),
        .ck_lsl1(ck_lsl1),
        .ck_lsl2(ck_lsl2),
        .ck_lsl3(ck_lsl3),
        .ck_lsl4(ck_lsl4),
        .ck_lsl5(ck_lsl5),
        .ck_lsl6(ck_lsl6),
        .ck_lsl7(ck_lsl7),
        .rst_n(rst_n),
        .tile_id(tile_id),
        .tie_hi(tie_hi),
        .tie_lo(tie_lo),
        .tap(tap),
        .t_out(t_out)
    );
endmodule
