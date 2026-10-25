`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// PL-BK (PARENTS-LANDED, 10-18): dsdv_bk_sel_x = dsdv_bk_sel (dsdv_bk_sel.sv) with its generate loop g_q[0..3] written
// out as plain instances u_q0..u_q3, the hard configuration (OT_DSDV_BK_HARD: no #() on u_g) and literal widths
// (CB 66, SB 865, OB 354).  Same children, same nets, same connections: it exists only because the landed-parent
// generator (tools/landed_parent/lp.py) needs a wires-only parent without generate.  Its landed form is
// dsdv_bk_sel_x_lp (generated; region plan tools/landed_parent/specs/dsdv_bk_sel_x.json).  Keep it in step with
// dsdv_bk_sel.sv: the PL-BK golden bench (run_bk_bench.sh sel ... with OT_DSDV_BK_LP) runs this structure.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_sel_x #(
    parameter integer V = 276
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    output wire          fault
);
    wire [514:0] l0, l1, l2, l3;
    wire [366:0] vd;   // packed (bk_g VD_PK)
    wire [V-1:0] vi_s_r, vi_n_r;
    wire rck_s, rck_n;
    wire [263:0] tc;
    wire [3:0] tcr;
    wire [3459:0] fs;
    wire [1415:0] fo;
    dsfd_dvrly_276_SN u_rs (.ck(clk), .rs(rst_n), .i(vi_s), .o(vi_s_r), .ck_o(rck_s));
    dsfd_dvrly_276_NS u_rn (.ck(clk), .rs(rst_n), .i(vi_n), .o(vi_n_r), .ck_o(rck_n));
    dsdv_bk_g u_g (.clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s_r), .vo_s(vo_s), .vi_n(vi_n_r), .vo_n(vo_n), .ln0(l0), .ln1(l1), .ln2(l2), .ln3(l3), .vd(vd), .fault(fault));
    dsdv_bksel_q u_q0 (.ck(clk), .rst(rst_n), .lane(l0), .f_c(tc[65:0]), .f_cr(tcr[0]), .t_s(fs[864:0]), .t_o(fo[353:0]));
    dsdv_bksel_q u_q1 (.ck(clk), .rst(rst_n), .lane(l1), .f_c(tc[131:66]), .f_cr(tcr[1]), .t_s(fs[1729:865]), .t_o(fo[707:354]));
    dsdv_bksel_q u_q2 (.ck(clk), .rst(rst_n), .lane(l2), .f_c(tc[197:132]), .f_cr(tcr[2]), .t_s(fs[2594:1730]), .t_o(fo[1061:708]));
    dsdv_bksel_q u_q3 (.ck(clk), .rst(rst_n), .lane(l3), .f_c(tc[263:198]), .f_cr(tcr[3]), .t_s(fs[3459:2595]), .t_o(fo[1415:1062]));
    dsdv_bksel_c u_c (.ck(clk), .rst(rst_n),
        .f_s_s(fs[1729:0]), .f_s_n(fs[3459:1730]), .f_o_s(fo[707:0]), .f_o_n(fo[1415:708]),
        .t_c_s(tc[131:0]), .t_c_n(tc[263:132]), .t_cr_s(tcr[1:0]), .t_cr_n(tcr[3:2]), .vd(vd));
endmodule
