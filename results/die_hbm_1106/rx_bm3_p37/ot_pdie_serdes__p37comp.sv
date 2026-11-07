// DIE-HBM-81 d44v part 37: plan form of the ot_pdie_serdes composition with the RX BM3 vB cut (HBM-GAPS-7).
// Same as ot_pdie_serdes__p20comp (results/die_hbm_1104/reform_b/split_p20) except u_rx = ot_pdie_serdes_rx__p37:
// residual u_rest (SEAM 7) + three BM natives u_bm0..2 on rck_clk; wires only.  The registered kit faces (+1 in/+1 out per
// hard-core pin, BM inputs S/ld/rs_n +1 relay = --face-in-stage) come from the kits, as in the proven bench form
// physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/gen_hg7/bench/ot_pdie_serdes__bm3fs.sv (runD BMIN 2 SEAM 7 PASS).
// Hard-core paths: <pdie>.u_fcore.u_core.u_rx.u_rest, <pdie>.u_fcore.u_core.u_rx.u_bm{0,1,2}.
`default_nettype none
module ot_pdie_serdes_rx__p37 (
    input wire clk, input wire rck_clk, input wire rst, output wire [511:0] rx, output wire [1:0] st, input wire [543:0] pma_rx,
    input wire e_flt_i, output wire [3:0] k_v, output wire [309:0] k_lo, output wire [4:0] k_L, output wire k_any,
    input wire [543:0] cw_q, input wire [7:0] apply, input wire o_unc, input wire [4:0] o_ne, input wire fs);
    wire [299:0] bm_S; wire [11:0] bm_ld, bm_done; wire bm_rs_n; wire [479:0] bm_lam; wire [449:0] bm_om; wire [14:0] bm_L; wire [2:0] bm_any;
    ot_pdie_serdes_rx_bm3_rest #(.BMTHC(1), .SEAM(7)) u_rest (.clk(clk), .rck_clk(rck_clk), .rst(rst), .rx(rx), .st(st),
        .pma_rx(pma_rx), .e_flt_i(e_flt_i), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw_q), .apply(apply),
        .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n),
        .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done));
    ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_bm0 (.clk(rck_clk), .rs_n(bm_rs_n), .ld(bm_ld[3:0]), .S(bm_S),
        .lam(bm_lam[159:0]), .om(bm_om[149:0]), .L(bm_L[4:0]), .any(bm_any[0]), .done(bm_done[3:0]));
    ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_bm1 (.clk(rck_clk), .rs_n(bm_rs_n), .ld(bm_ld[7:4]), .S(bm_S),
        .lam(bm_lam[319:160]), .om(bm_om[299:150]), .L(bm_L[9:5]), .any(bm_any[1]), .done(bm_done[7:4]));
    ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_bm2 (.clk(rck_clk), .rs_n(bm_rs_n), .ld(bm_ld[11:8]), .S(bm_S),
        .lam(bm_lam[479:320]), .om(bm_om[449:300]), .L(bm_L[14:10]), .any(bm_any[2]), .done(bm_done[11:8]));
endmodule
module ot_pdie_serdes__p37comp (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    wire ef; wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L; wire k_any;
    wire [543:0] cw_q; wire [7:0] apply; wire o_unc; wire [4:0] o_ne; wire fs;
    ot_pdie_serdes_tx u_tx (.clk(clk), .rst(rst), .tx(tx), .pma_tx(pma_tx), .e_flt_o(ef));
    assign pma_tck = clk;
    ot_pdie_serdes_rx__p37 u_rx (.clk(clk), .rck_clk(pma_rck), .rst(rst), .rx(rx), .st(st), .pma_rx(pma_rx), .e_flt_i(ef),
        .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs));
    ot_s81_kp4_dchn u_chn (.clk(pma_rck), .rst_n(rst), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(), .n_unc());
endmodule
module ot_pdie_serdes__p37fcore (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    ot_pdie_serdes__p37comp u_core (.clk(clk), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule
// plan module ot_pdie_serdes (thin parent glue, wires only), p37 form
module ot_pdie_serdes__p37glue (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    ot_pdie_serdes__p37fcore u_fcore (.clk(clk), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck));
endmodule
`default_nettype wire
