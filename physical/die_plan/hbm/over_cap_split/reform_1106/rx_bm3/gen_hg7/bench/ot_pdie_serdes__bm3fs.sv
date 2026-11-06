// HBM-GAPS-7 bench: BM3 safe form. residual rest #(SEAM) under a face shell on ALL signal ports (clk), three BM natives each
// under a face shell (rck_clk) on all signal ports. BMUT: 1 = BM0 ld seam without its BM-side FF; 2 = residual bm_lam without FF.
`default_nettype none
module ot_rx_bm3_rest_fs #(parameter integer SEAM = 6, parameter integer BMUT = 0) (
    input wire clk, input wire rck_clk, input wire rst, output reg [511:0] rx, output reg [1:0] st, input wire [543:0] pma_rx,
    input wire e_flt_i, output reg [3:0] k_v, output reg [309:0] k_lo, output reg [4:0] k_L, output reg k_any,
    input wire [543:0] cw_q, input wire [7:0] apply, input wire o_unc, input wire fs,
    output reg [299:0] bm_S, output reg [11:0] bm_ld, output reg bm_rs_n,
    input wire [479:0] bm_lam, input wire [449:0] bm_om, input wire [14:0] bm_L, input wire [2:0] bm_any, input wire [11:0] bm_done);
    reg [543:0] pma_q, cw_qq; reg ef_q, unc_q, fs_q; reg [7:0] ap_q;
    reg [479:0] lam_q; reg [449:0] om_q; reg [14:0] L_q; reg [2:0] any_q; reg [11:0] dn_q;
    wire [511:0] rx_c; wire [1:0] st_c; wire [3:0] kv_c; wire [309:0] klo_c; wire [4:0] kL_c; wire kany_c;
    wire [299:0] S_c; wire [11:0] ld_c; wire rs_c;
    always @(posedge clk) begin
        pma_q <= pma_rx; cw_qq <= cw_q; ef_q <= e_flt_i; unc_q <= o_unc; fs_q <= fs; ap_q <= apply;
        lam_q <= bm_lam; om_q <= bm_om; L_q <= bm_L; any_q <= bm_any; dn_q <= bm_done;
        rx <= rx_c; st <= st_c; k_v <= kv_c; k_lo <= klo_c; k_L <= kL_c; k_any <= kany_c; bm_S <= S_c; bm_ld <= ld_c; bm_rs_n <= rs_c;
    end
    ot_pdie_serdes_rx_bm3_rest #(.BMTHC(1), .SEAM(SEAM)) u_fcore (.clk(clk), .rck_clk(rck_clk), .rst(rst), .rx(rx_c), .st(st_c),
        .pma_rx(pma_q), .e_flt_i(ef_q), .k_v(kv_c), .k_lo(klo_c), .k_L(kL_c), .k_any(kany_c), .cw_q(cw_qq), .apply(ap_q),
        .o_unc(unc_q), .o_ne(5'd0), .fs(fs_q), .bm_S(S_c), .bm_ld(ld_c), .bm_rs_n(rs_c),
        .bm_lam((BMUT == 2) ? bm_lam : lam_q), .bm_om(om_q), .bm_L(L_q), .bm_any(any_q), .bm_done(dn_q));
endmodule
module ot_rx_bm_native_fs #(parameter integer NOLD = 0) (
    input wire clk, input wire rs_n, input wire [3:0] ld, input wire [299:0] S,
    output reg [159:0] lam, output reg [149:0] om, output reg [4:0] L, output reg any, output reg [3:0] done);
    reg rs_q; reg [3:0] ld_q; reg [299:0] S_q;
    wire [159:0] lam_c; wire [149:0] om_c; wire [4:0] L_c; wire any_c; wire [3:0] dn_c;
    always @(posedge clk) begin rs_q <= rs_n; ld_q <= ld; S_q <= S; lam <= lam_c; om <= om_c; L <= L_c; any <= any_c; done <= dn_c; end
    ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_fcore (.clk(clk), .rs_n(rs_q), .ld((NOLD != 0) ? ld : ld_q), .S(S_q),
        .lam(lam_c), .om(om_c), .L(L_c), .any(any_c), .done(dn_c));
endmodule
module ot_rx_bm3fs #(parameter integer SEAM = 6, parameter integer BMUT = 0) (
    input wire clk, input wire rck_clk, input wire rst, output wire [511:0] rx, output wire [1:0] st, input wire [543:0] pma_rx,
    input wire e_flt_i, output wire [3:0] k_v, output wire [309:0] k_lo, output wire [4:0] k_L, output wire k_any,
    input wire [543:0] cw_q, input wire [7:0] apply, input wire o_unc, input wire fs);
    wire [299:0] bm_S; wire [11:0] bm_ld, bm_done; wire bm_rs_n; wire [479:0] bm_lam; wire [449:0] bm_om; wire [14:0] bm_L; wire [2:0] bm_any;
    ot_rx_bm3_rest_fs #(.SEAM(SEAM), .BMUT(BMUT)) u_rest (.clk(clk), .rck_clk(rck_clk), .rst(rst), .rx(rx), .st(st), .pma_rx(pma_rx),
        .e_flt_i(e_flt_i), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .fs(fs),
        .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n), .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done));
    for (genvar e = 0; e < 3; e = e + 1) begin : g_bm
        ot_rx_bm_native_fs #(.NOLD(((BMUT == 1) && (e == 0)) ? 1 : 0)) u_bm (.clk(rck_clk), .rs_n(bm_rs_n), .ld(bm_ld[4*e+:4]), .S(bm_S),
            .lam(bm_lam[160*e+:160]), .om(bm_om[150*e+:150]), .L(bm_L[5*e+:5]), .any(bm_any[e]), .done(bm_done[4*e+:4]));
    end
endmodule
// p20fs bench form with rx replaced by the BM3 face-shelled form (TX and dchn unchanged)
module ot_pdie_serdes__p20fs #(parameter integer SMUT = 0, parameter integer SEAM = 6, parameter integer BMUT = 0) (
    input wire clk, input wire rst, input wire [511:0] tx, output wire [511:0] rx, output wire [1:0] st,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck);
    wire ef; wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L; wire k_any;
    wire [543:0] cw_q; wire [7:0] apply; wire o_unc; wire [4:0] o_ne; wire fs;
    wire [309:0] k_lo_m = (SMUT == 9) ? {k_lo[309:1], ~k_lo[0]} : k_lo;
    ot_pdie_serdes_tx__fs u_tx (.clk(clk), .rst(rst), .tx(tx), .pma_tx(pma_tx), .e_flt_o(ef));
    assign pma_tck = clk;
    ot_rx_bm3fs #(.SEAM(SEAM), .BMUT(BMUT)) u_rx (.clk(clk), .rck_clk(pma_rck), .rst(rst), .rx(rx), .st(st), .pma_rx(pma_rx), .e_flt_i(ef),
        .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .fs(fs));
    ot_s81_kp4_dchn u_chn (.clk(pma_rck), .rst_n(rst), .k_v(k_v), .k_lo(k_lo_m), .k_L(k_L), .k_any(k_any),
        .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(), .n_unc());
endmodule
`default_nettype wire
