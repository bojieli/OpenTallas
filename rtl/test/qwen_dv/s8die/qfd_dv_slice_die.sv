// TOK-QW 10-24: the BOUND compute-die slice at chain position SIDX, for tb_qfd_dv2 FACE 3 (testbench wrapper, no logic).
// physical/die_plan/qwen_compute/bind/asbuilt_tie.json (bound_r8): qfd_dv_slice2 is substituted by qfd_dv_s8_flat, and the
// chain ends by their QC-P4 / QC-P5-TIE variants (substitute_parent):
//   dvs_W5 -> qfd_dv_s8_ce_w5 (l9 pair head, no sc_up_i), dvs_(W3|W1|E1|E3) -> qfd_dv_s8_ce_l9h (l9 pair head, no l9_i),
//   dvs_E5 -> qfd_dv_s8_ce_e5 (far end: no l9_i / st_dn_i / sc_dn_i / ch_up_i / ag_up_i), every other slice qfd_dv_s8_flat.
// tb_qfd_dv2 chain order: slice 0 = W5 (down end, next to tt_ctlm) ... 5 = W0, 6 = E0 ... 11 = E5 (TREQ_HOPS order of
// bound_r8/regen/constants.json).  treq_i / treq_o = the bound table-request lane (tt_ctlm -> W5 -> ... -> E5).
// The ports a variant does not have are the ones tb_qfd_dv2 ties to 0 at that position (unused here).
`timescale 1ns/1ps
module qfd_dv_slice_die #(parameter integer SIDX = 0) (
    input  wire ck, input wire rst_n,
    input  wire [115:0] cmd_i, output wire [115:0] cmd_o, input wire [452:0] hr_i, output wire [452:0] hr_o,
    input  wire [1027:0] rs_s, input wire [1027:0] rs_n, input wire [513:0] l9_i, output wire [513:0] l9_o,
    input  wire [1087:0] st_up_i, output wire [1087:0] st_up_o, input wire [1087:0] st_dn_i, output wire [1087:0] st_dn_o,
    input  wire [47:0] sc_up_i, output wire [47:0] sc_up_o, input wire [47:0] sc_dn_i, output wire [47:0] sc_dn_o,
    input  wire [1094:0] ch_up_i, output wire [1094:0] ch_dn_o, input wire [1037:0] ch_dn_i, output wire [1037:0] ch_up_o,
    output wire [515:0] cw_n0, cw_n1, cw_n2, cw_n3, cw_s0, cw_s1, cw_s2, cw_s3,
    output wire [106:0] st, output wire [49:0] cc_o, input wire [9:0] ag_up_i, output wire [9:0] ag_dn_o,
    input  wire [8:0] treq_i, output wire [8:0] treq_o,
    // testbench probes: VM write port (w16, filtered by address in the bench), heads x tap, heads fault
    output wire vw_v, output wire [23:0] vw_a, output wire xt_v, output wire [23:0] xt_a, output wire hd_fault);
    generate if (SIDX == 0) begin : g_w5
        qfd_dv_s8_ce_w5 u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o), .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n),
            .l9_o(l9_o), .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_i(st_dn_i), .st_dn_o(st_dn_o),
            .sc_up_o(sc_up_o), .sc_dn_i(sc_dn_i), .sc_dn_o(sc_dn_o), .ch_up_i(ch_up_i), .ch_dn_o(ch_dn_o), .ch_dn_i(ch_dn_i),
            .ch_up_o(ch_up_o), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0), .cw_s1(cw_s1),
            .cw_s2(cw_s2), .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_up_i(ag_up_i), .ag_dn_o(ag_dn_o), .treq_i(treq_i), .treq_o(treq_o));
        assign vw_v = u.w16_we; assign vw_a = u.w16_addr; assign xt_v = u.xt_v; assign xt_a = u.xt_a;
        assign hd_fault = u.fch0 | u.fch1 | u.fch2 | u.fch3;
    end else if (SIDX == 11) begin : g_e5
        qfd_dv_s8_ce_e5 u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o), .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n),
            .l9_o(l9_o), .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_o(st_dn_o),
            .sc_up_i(sc_up_i), .sc_up_o(sc_up_o), .sc_dn_o(sc_dn_o), .ch_dn_o(ch_dn_o), .ch_dn_i(ch_dn_i),
            .ch_up_o(ch_up_o), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0), .cw_s1(cw_s1),
            .cw_s2(cw_s2), .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_dn_o(ag_dn_o), .treq_i(treq_i), .treq_o(treq_o));
        assign vw_v = u.w16_we; assign vw_a = u.w16_addr; assign xt_v = u.xt_v; assign xt_a = u.xt_a;
        assign hd_fault = u.fch0 | u.fch1 | u.fch2 | u.fch3;
    end else if (SIDX == 2 || SIDX == 4 || SIDX == 7 || SIDX == 9) begin : g_l9h
        qfd_dv_s8_ce_l9h u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o), .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n),
            .l9_o(l9_o), .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_i(st_dn_i), .st_dn_o(st_dn_o),
            .sc_up_i(sc_up_i), .sc_up_o(sc_up_o), .sc_dn_i(sc_dn_i), .sc_dn_o(sc_dn_o), .ch_up_i(ch_up_i), .ch_dn_o(ch_dn_o),
            .ch_dn_i(ch_dn_i), .ch_up_o(ch_up_o), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0),
            .cw_s1(cw_s1), .cw_s2(cw_s2), .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_up_i(ag_up_i), .ag_dn_o(ag_dn_o),
            .treq_i(treq_i), .treq_o(treq_o));
        assign vw_v = u.w16_we; assign vw_a = u.w16_addr; assign xt_v = u.xt_v; assign xt_a = u.xt_a;
        assign hd_fault = u.fch0 | u.fch1 | u.fch2 | u.fch3;
    end else begin : g_flat
        qfd_dv_s8_flat u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o), .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n),
            .l9_i(l9_i), .l9_o(l9_o), .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_i(st_dn_i), .st_dn_o(st_dn_o),
            .sc_up_i(sc_up_i), .sc_up_o(sc_up_o), .sc_dn_i(sc_dn_i), .sc_dn_o(sc_dn_o), .ch_up_i(ch_up_i), .ch_dn_o(ch_dn_o),
            .ch_dn_i(ch_dn_i), .ch_up_o(ch_up_o), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0),
            .cw_s1(cw_s1), .cw_s2(cw_s2), .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_up_i(ag_up_i), .ag_dn_o(ag_dn_o),
            .treq_i(treq_i), .treq_o(treq_o));
        assign vw_v = u.w16_we; assign vw_a = u.w16_addr; assign xt_v = u.xt_v; assign xt_a = u.xt_a;
        assign hd_fault = u.fch0 | u.fch1 | u.fch2 | u.fch3;
    end endgenerate
endmodule
