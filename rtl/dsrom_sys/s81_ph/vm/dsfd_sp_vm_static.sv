`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_vm (STATIC revision s1, claude S81 VM owner r8, 2026-10-14): the S81 layer-die VM master under its die name,
// a cluster over real RTL (plus one registered producer-status check): dsfd_vm_static_core (stream 1.2 GHz: 128 real SRAM banks, fixed-rule read /
// write service, engine 12, static LARM landing) + three fixed-phase 3:4 serial -> stream transfers ot_s81_vm_x34
// for the serial-domain row producers (selector, collector, HBM scan service SW).
// Owner rules 2026-10-14T18:59 / 19:12: static cycle schedule, no credits / backpressure / ready-driven issue; all
// on-chip execution real hardware.  Every port below lands on real RTL; there is no tied functional port.
//
// PORTS (directions are the VM's; widths are the die nets):
//   ck / rst          serial 0.9 GHz clock / async low reset (the x34 serial halves)
//   cks / rss         stream 1.2 GHz clock / async low reset (core + x34 stream halves); STARTUP CONTRACT: both resets
//                     released on the common epoch (x34 header); a misalignment raises the VM fault (c_st[0])
//   c_cmd 85 / c_done 9 / c_st 2       sequencer engine 12 (dsfd_vm_seq_static: done = command pin + 6)
//   t_inp_su / t_inp_hc                verified-operand levels (assertion feeds, never an issue gate)
//   f_su_rqv 16, f_su_rq 224 -> t_su_rsv 16, t_su_rs 8192          L 12 stream edges (pin -> output register)
//   f_su_wqv 16, f_su_wq 224, f_su_wqm 256, f_su_wqd 8192           write sources 0..15
//   f_hc_rqv 2, f_hc_rq 28 -> t_hc_rsv 2, t_hc_rs 1024              L 12
//   f_hc_wqv 8, f_hc_wq 112, f_hc_wqm 128, f_hc_wqd 4096            write sources 16..23
//   f_pqx 20 {x_addr 19, x_re} -> t_pqx 2049 {x_q 2048, x_rv}         L 12 (fixed: the PQ's 'credit window' is void)
//   sel 515 / col 515 {fault, live, row 512, v}   serial; landing lanes 2 / 3 (LARM groups 5 / 6)
//   aSW 1027 {fault, live, rows 1024, v}          serial; landing lanes 0 / 1 (LARM group 0)
//   f_collective 2204   NEW static collective -> VM rows: 4 x {tag 8, data 512, mask 16, row 14, v} (write sources
//                       44..47, compiler rows; REPLACES the legacy 2,100-b cfifo record + tcs room bits)
//   f_crq 15 {row 14, v} -> t_crs 513 {row 512, v}   NEW static collective source-row read, L 12 (REPLACES the
//                       legacy VM -> collective t_collective 592 push)
// NOT IN THIS REVISION (no static RTL yet; the die must not wire them to this master, port-bind stays FAIL on their
// producers until they exist): f_capture 13376 (static capture row assembly), f_wfc 560 / t_wfc 1029 (WFC kit:
// grant handshake = dynamic), t_gather 512 / f_xgo 11 (no defined VM function), qSW 513 / qSWs 3 (VM -> scan request
// lane), tcs 3 (room = backpressure, void).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_sp_vm (
    input  wire [0:0]    ck, rst, cks, rss,
    input  wire [84:0]   c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    output wire [0:0]    t_inp_su, t_inp_hc,
    input  wire [15:0]   f_su_rqv, input wire [223:0] f_su_rq, output wire [15:0] t_su_rsv, output wire [8191:0] t_su_rs,
    input  wire [15:0]   f_su_wqv, input wire [223:0] f_su_wq, input wire [255:0] f_su_wqm, input wire [8191:0] f_su_wqd,
    input  wire [1:0]    f_hc_rqv, input wire [27:0] f_hc_rq, output wire [1:0] t_hc_rsv, output wire [1023:0] t_hc_rs,
    input  wire [7:0]    f_hc_wqv, input wire [111:0] f_hc_wq, input wire [127:0] f_hc_wqm, input wire [4095:0] f_hc_wqd,
    input  wire [19:0]   f_pqx, output wire [2048:0] t_pqx,
    input  wire [514:0]  sel, col,
    input  wire [1026:0] aSW,
    input  wire [2203:0] f_collective,
    input  wire [14:0]   f_crq, output wire [512:0] t_crs
);
    // ---------------------------------------------------------------- serial -> stream fixed-phase transfers
    wire xs_v, xc_v, xw_v; wire [513:0] xs_d, xc_d; wire [1025:0] xw_d; wire [2:0] x_al;
    ot_s81_vm_x34 #(.W(514)) u_xsel (.s_ck(ck[0]), .s_rst_n(rst[0]), .s_v(sel[0]), .s_d(sel[514:1]),
        .t_ck(cks[0]), .t_rst_n(rss[0]), .o_v(xs_v), .o_d(xs_d), .fault(x_al[0]));
    ot_s81_vm_x34 #(.W(514)) u_xcol (.s_ck(ck[0]), .s_rst_n(rst[0]), .s_v(col[0]), .s_d(col[514:1]),
        .t_ck(cks[0]), .t_rst_n(rss[0]), .o_v(xc_v), .o_d(xc_d), .fault(x_al[1]));
    ot_s81_vm_x34 #(.W(1026)) u_xsw (.s_ck(ck[0]), .s_rst_n(rst[0]), .s_v(aSW[0]), .s_d(aSW[1026:1]),
        .t_ck(cks[0]), .t_rst_n(rss[0]), .o_v(xw_v), .o_d(xw_d), .fault(x_al[2]));
    // producer status, stream side (registered): a row from a producer that is not live, or a producer fault, is a VM fault
    reg p_bad;
    always @(posedge cks[0] or negedge rss[0])
        if (!rss[0]) p_bad <= 1'b0;
        else if ((xs_v && !xs_d[512]) || (xc_v && !xc_d[512]) || (xw_v && !xw_d[1024]) ||
                 (xs_v && xs_d[513]) || (xc_v && xc_d[513]) || (xw_v && xw_d[1025])) p_bad <= 1'b1;
    wire vm_fault;
    dsfd_vm_static_core u_core (.cks(cks[0]), .rss(rss[0]), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .t_inp_su(t_inp_su[0]), .t_inp_hc(t_inp_hc[0]),
        .f_su_rqv(f_su_rqv), .f_su_rq(f_su_rq), .t_su_rsv(t_su_rsv), .t_su_rs(t_su_rs),
        .f_su_wqv(f_su_wqv), .f_su_wq(f_su_wq), .f_su_wqm(f_su_wqm), .f_su_wqd(f_su_wqd),
        .f_hc_rqv(f_hc_rqv), .f_hc_rq(f_hc_rq), .t_hc_rsv(t_hc_rsv), .t_hc_rs(t_hc_rs),
        .f_hc_wqv(f_hc_wqv), .f_hc_wq(f_hc_wq), .f_hc_wqm(f_hc_wqm), .f_hc_wqd(f_hc_wqd),
        .f_pqx(f_pqx), .t_pqx(t_pqx), .f_crq(f_crq), .t_crs(t_crs),
        .l_v({xc_v, xs_v, xw_v, xw_v}), .l_d({xc_d[511:0], xs_d[511:0], xw_d[1023:512], xw_d[511:0]}),
        .f_cvm(f_collective), .x_flt(|x_al | p_bad), .vm_fault(vm_fault));
endmodule
`default_nettype wire
