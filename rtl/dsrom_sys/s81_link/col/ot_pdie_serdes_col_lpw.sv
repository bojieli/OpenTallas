`timescale 1ns/1ps
// S81-SERDES 10-19: BENCH WRAPPER ot_pdie_serdes_col (same ports as ot_pdie_serdes) around the generated landed column
// ot_pdie_serdes_col_lp: the core clock clk drives the clk-family region roots (ck_tx, ck_ptx), the recovered clock
// pma_rck the rck-family roots (ck_syn, ck_dly, ck_chn, ck_out) -- the die delivers exactly this (record die_obligations).
// Used by tb_s81_pdie_col (two dies, die B 300 ppm slow: pma_rck is NOT clk, so the CDC children are really exercised).
// Never a kit source (the kit top is ot_pdie_serdes_col_lp).
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
    ot_pdie_serdes_col_lp #(.MUT(MUT)) u_lp (.ck_tx(clk), .ck_ptx(clk), .ck_syn(pma_rck), .ck_dly(pma_rck), .ck_chn(pma_rck),
        .ck_out(pma_rck), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx));
endmodule
