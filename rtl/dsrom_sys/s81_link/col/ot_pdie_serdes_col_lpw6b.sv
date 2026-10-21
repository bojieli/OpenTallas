`timescale 1ns/1ps
// DRIVE-S81-PHY 10-20 lpw6: lpw5 around the lp6b landed column (one decoder region ck_dec, regional reset ports rst_<r>).
// S81-LINK4 10-20 lpw5: copy of lpw4 around the lp5 landed column (NATIVE32 landings + rate matcher).
// S81-LINK3 10-19 lpk5: BENCH WRAPPER ot_pdie_serdes_col (same ports as ot_pdie_serdes) around the generated landed column
// ot_pdie_serdes_col_lp5: the core clock clk drives the clk-family region roots (ck_tx, ck_r0, ck_r1, ck_ptx, ck_rxo), the
// recovered clock pma_rck the rck-family roots (ck_syn, ck_dly, ck_chn, ck_out) -- the die delivers exactly this (record
// die_obligations).  Used by tb_s81_pdie_col (two dies, die B 300 ppm slow).  Never a kit source (kit top ot_pdie_serdes_col_lp5).
module ot_pdie_serdes_col #(parameter integer PMA_LAT = 4, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck
);
    ot_pdie_serdes_col_lp6b #(.MUT(MUT)) u_lp (.ck_tx(clk), .ck_r0(clk), .ck_r1(clk), .ck_ptx(clk), .ck_rxo(clk),
        .ck_dec(pma_rck),
        .rst_tx(rst), .rst_r0(rst), .rst_r1(rst), .rst_ptx(rst), .rst_rxo(rst), .rst_dec(rst), .rst_prx(rst), .ck_prx(pma_rck), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx));
endmodule
