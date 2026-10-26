`timescale 1ns/1ps
// Local ROM-pair clock roots: each raw ROM shares a root with its capture and
// complete expansion/return pipeline. RQR north/south each has a compact root.
// Pure clock rewiring around the unchanged rp2_45 body: zero added edges.
// Q-ROMPARENT 10-16 21:00 (_rr): REGROOT 1 adds four regional roots: ck_rsw/ck_rnw = west-column halves of the RQR
// group words (east halves stay on ck_rs/ck_rn), ck_dw/ck_de = west/east halves of mq_wrom + s2_w. Zero added edges.
// Q-ROMPARENT 10-16 18:40: the eight TX roots ck_tx0..7 are separate compensated entries again (gate3 measured the
// shared ck root at TT 556..1230 ps over 10,644 sinks); each TX root owns only its LSL's two rungs + reset relay.
module qfd_tile_nl_rp2_romleaf_rr #(
    parameter integer G4_ROOTS = 1,
    parameter integer REGROOT_MODE = 3
`ifndef SYNTHESIS
  , parameter integer ROM_TILE = -1
`endif
) (
    input  wire          ck,
    input  wire          ck_rp0,
    input  wire          ck_rp1,
    input  wire          ck_rp2,
    input  wire          ck_rp3,
    input  wire          ck_rp4,
    input  wire          ck_rp5,
    input  wire          ck_rp6,
    input  wire          ck_rp7,
    input  wire          ck_rp8,
    input  wire          ck_rp9,
    input  wire          ck_tx0,
    input  wire          ck_tx1,
    input  wire          ck_tx2,
    input  wire          ck_tx3,
    input  wire          ck_tx4,
    input  wire          ck_tx5,
    input  wire          ck_tx6,
    input  wire          ck_tx7,
    input  wire          ck_rsw,
    input  wire          ck_rnw,
    input  wire          ck_dw,
    input  wire          ck_de,
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
    qfd_tile_nl_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
`else
    qfd_tile_nl_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE)) u_g (
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
