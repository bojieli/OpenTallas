`timescale 1ns/1ps
// HBM-UCIE8 10-20: BENCH WRAPPER ot_pdie_ucie_col_w (same ports as ot_pdie_ucie) around the generated landed column
// ot_pdie_ucie_col: the core clock clk drives region roots ck_tx and ck_rx (HBM-UCIE9 split), pma_rck region root ck_rck; the die
// reset rst drives both regional reset ports (the die delivers exactly this: one clock + one reset per region, released
// on the same edge; record die_obligations).  Used by tb_pdie_ucie_col.  Never a kit source (kit top ot_pdie_ucie_col).
module ot_pdie_ucie_col_w #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [512:0]  pma_tx,
    output wire          pma_tck,
    input  wire [512:0]  pma_rx,
    input  wire          pma_rck
);
    ot_pdie_ucie_col #(.MUT(MUT)) u_lp (.ck_tx(clk), .ck_rx(clk), .ck_rck(pma_rck), .rst_tx(rst), .rst_rx(rst), .rst_rck(rst), .tx(tx), .rx(rx),
        .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx));
endmodule
