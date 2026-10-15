`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_vm (STATIC revision s2, claude S81 VM owner r9, 2026-10-14): the S81 layer-die VM master under its die
// name, a cluster over real RTL only.  s2 binds ALL 40 die ports of the S-BIND v20 list (s1 bound 31):
//   dsfd_vm_static_core  stream 1.2 GHz: 128 real SRAM banks, fixed-rule read / write service, engine 12, static LARM
//   dsfd_vm_static_cap   capture face: 16 static row-assembly lanes (serial) + 16 fixed-phase 3:4 transfers
//   dsfd_vm_static_wfc   WFC kit VM channels: one write + one read pair a serial cycle, constant grants, fixed return
//   dsfd_vm_static_xio   outbound row streams (collective records, scan queries, gather phase words), collective
//                        landing + fixed source-row service / phase-stage assertions
//   ot_s81_vm_x34 x 3    serial landing producers (selector, collector, HBM scan service SW)
// Owner rules 2026-10-14T18:59 / 19:12: static cycle schedule, no credits / backpressure / ready-driven issue; all
// on-chip execution real hardware.  Every port lands on real RTL; no functional port is tied.
//
// PORTS (directions the VM's; widths = the die nets; domain: S serial ck/rst 0.9 GHz, T stream cks/rss 1.2 GHz):
//   ck rst (S) / cks rss (T)   STARTUP CONTRACT: both resets released on the common 3:4 epoch (x34 / x43 headers)
//   c_cmd 85 / c_done 9 / c_st 2 (T)    sequencer engine 12 (done = command pin + 6); t_inp_su / t_inp_hc (T)
//   SU 16 rd + 16 wr / HC 2 rd + 8 wr row slots (T), f_pqx 20 -> t_pqx 2049 (T)              L 12 reads
//   sel 515 / col 515 / aSW 1027 (S)      landing producers (static LARM groups 5 / 6 / 0)
//   f_capture 13376 (S)                   dsfd_sp_capture_c t_vm: static capture rows (write sources 32..43, 48..51)
//   f_wfc 560 (S) -> t_wfc 1029 (S)       dsfd_wfc_stg VM channels (write source 52, aux reads 8..11)
//   f_collective 2204 (T)                 four compiler-addressed static row writes (sources 44..47)
//   f_crq 15 / t_crs 513 (T)              collective fixed-latency source-row service; no credits or room
//   t_gather 512 (S) / f_xgo 11 (T)       -> dsfd_sp_gather_c f_vm phase words (STREAM dest 1); xgo = assertion feed
//   qSW 513 (S) / qSWs 3 (S)              -> scan service query lane end block (STREAM dest 0); qSWs = assertion feed
// Engram MIX4 (20R/4W, dsfd_engram_mix4_c) is built in the core; its die ports appear under
// +define+DSFD_SP_VM_MIX4 once the die wires the MIX4 slot (no die net today: without the define the core's MIX
// inputs are held idle and its outputs unread, the MIX function is absent from this die revision, not stubbed).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_sp_vm #(parameter integer CAP_PIPE=0, parameter integer READ_PIPE=0) (
    input  wire          ck_core_t, ck_rsched_t, ck_seq_t, ck_landing_t,
    input  wire [15:0]   ck_mem_fsr_t,
    input  wire [3:0]    ck_mem_return_t,
    input  wire [127:0]  ck_mem_bank_t, ck_mem_wcapture_t,
    input  wire [15:0]   ck_mem_wscatter_t,
    input  wire [47:0]   ck_mem_relay_req_t, ck_mem_relay_rsp_t,
    input  wire          ck_write_control_t, ck_write_header_t,
    input  wire [3:0]    ck_write_payload_t,
    input  wire [15:0]   ck_write_dispatch_t,
    input  wire [127:0]  ck_write_stage_t,
    input  wire [2:0]    ck_landing_x34_s, ck_landing_x34_t,
    input  wire          rss_core_t, rss_rsched_t, rss_seq_t, rss_landing_t,
    input  wire [15:0]   rss_mem_fsr_t,
    input  wire [3:0]    rss_mem_return_t,
    input  wire [127:0]  rss_mem_bank_t, rss_mem_wcapture_t,
    input  wire [15:0]   rss_mem_wscatter_t,
    input  wire [47:0]   rss_mem_relay_t,
    input  wire          rss_write_control_t, rss_write_header_t,
    input  wire [3:0]    rss_write_payload_t,
    input  wire [15:0]   rss_write_dispatch_t,
    input  wire [127:0]  rss_write_stage_t,
    input  wire [2:0]    rst_landing_x34_s, rss_landing_x34_t,
    input  wire          ck_cap_control_s, rst_cap_control_s,
    input  wire [15:0]   ck_cap_lane_s, ck_cap_x34_s, ck_cap_x34_t,
    input  wire [15:0]   rst_cap_x34_s, rss_cap_x34_t,
    input  wire          ck_wfc_control_s, ck_wfc_control_t, ck_wfc_x34_s, ck_wfc_x34_t, ck_wfc_x43_s, ck_wfc_x43_t,
    input  wire          rst_wfc_control_s, rss_wfc_control_t, rst_wfc_x34_s, rss_wfc_x34_t, rst_wfc_x43_s, rss_wfc_x43_t,
    input  wire          ck_xio_control_s, ck_xio_control_t, rst_xio_control_s, rss_xio_control_t,
    input  wire [1:0]    ck_xio_x43_s, ck_xio_x43_t, rst_xio_x43_s, rss_xio_x43_t,
    input  wire [63:0]   ck_read_data_t, rss_read_data_t,
    input  wire [7:0]    ck_read_valid_t, rss_read_valid_t,
    input  wire [84:0]   c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    output wire [0:0]    t_inp_su, t_inp_hc,
    input  wire [15:0]   f_su_rqv, input wire [223:0] f_su_rq, output wire [15:0] t_su_rsv, output wire [8191:0] t_su_rs,
    input  wire [15:0]   f_su_wqv, input wire [223:0] f_su_wq, input wire [255:0] f_su_wqm, input wire [8191:0] f_su_wqd,
    input  wire [1:0]    f_hc_rqv, input wire [27:0] f_hc_rq, output wire [1:0] t_hc_rsv, output wire [1023:0] t_hc_rs,
    input  wire [7:0]    f_hc_wqv, input wire [111:0] f_hc_wq, input wire [127:0] f_hc_wqm, input wire [4095:0] f_hc_wqd,
    input  wire [19:0]   f_pqx, output wire [2048:0] t_pqx,
    input  wire [514:0]  sel, col,
    input  wire [1026:0] aSW,
    input  wire [13375:0] f_capture,
    input  wire [559:0]  f_wfc, output wire [1028:0] t_wfc,
    input  wire [2203:0] f_collective, input wire [14:0] f_crq, output wire [512:0] t_crs,
    output wire [511:0]  t_gather, input wire [10:0] f_xgo,
    output wire [512:0]  qSW, input wire [2:0] qSWs
`ifdef DSFD_SP_VM_MIX4
    , input  wire [19:0] f_mx_rqv, input wire [279:0] f_mx_rq, output wire [19:0] t_mx_rsv, output wire [10239:0] t_mx_rs
    , input  wire [3:0]  f_mx_wqv, input wire [55:0] f_mx_wq, input wire [63:0] f_mx_wqm, input wire [2047:0] f_mx_wqd
`endif
);
`ifndef DSFD_SP_VM_MIX4
    wire [19:0] f_mx_rqv = 20'd0; wire [279:0] f_mx_rq = 280'd0; wire [19:0] t_mx_rsv; wire [10239:0] t_mx_rs;
    wire [3:0] f_mx_wqv = 4'd0; wire [55:0] f_mx_wq = 56'd0; wire [63:0] f_mx_wqm = 64'd0; wire [2047:0] f_mx_wqd = 2048'd0;
`endif
    // ---------------------------------------------------------------- serial -> stream landing transfers
    wire xs_v, xc_v, xw_v; wire [513:0] xs_d, xc_d; wire [1025:0] xw_d; wire [2:0] x_al;
    ot_s81_vm_x34 #(.W(514)) u_xsel (.s_ck(ck_landing_x34_s[0]), .s_rst_n(rst_landing_x34_s[0]), .s_v(sel[0]), .s_d(sel[514:1]),
        .t_ck(ck_landing_x34_t[0]), .t_rst_n(rss_landing_x34_t[0]), .o_v(xs_v), .o_d(xs_d), .fault(x_al[0]));
    ot_s81_vm_x34 #(.W(514)) u_xcol (.s_ck(ck_landing_x34_s[1]), .s_rst_n(rst_landing_x34_s[1]), .s_v(col[0]), .s_d(col[514:1]),
        .t_ck(ck_landing_x34_t[1]), .t_rst_n(rss_landing_x34_t[1]), .o_v(xc_v), .o_d(xc_d), .fault(x_al[1]));
    ot_s81_vm_x34 #(.W(1026)) u_xsw (.s_ck(ck_landing_x34_s[2]), .s_rst_n(rst_landing_x34_s[2]), .s_v(aSW[0]), .s_d(aSW[1026:1]),
        .t_ck(ck_landing_x34_t[2]), .t_rst_n(rss_landing_x34_t[2]), .o_v(xw_v), .o_d(xw_d), .fault(x_al[2]));
    // landing header checks and the edge-fault levels are registered in the engine-12 tile (dsfd_vm_seq_tile, ck_seq_t)
    // ---------------------------------------------------------------- edge services
    wire [15:0] cp_v; wire [223:0] cp_row; wire [255:0] cp_m; wire [8191:0] cp_d; wire cap_f;
    dsfd_vm_static_cap #(.CAP_PIPE(CAP_PIPE)) u_cap (
        .ck_control_s(ck_cap_control_s), .rst_control_s(rst_cap_control_s), .ck_lane_s(ck_cap_lane_s),
        .ck_x34_s(ck_cap_x34_s), .ck_x34_t(ck_cap_x34_t), .rst_x34_s(rst_cap_x34_s), .rss_x34_t(rss_cap_x34_t), .f_capture(f_capture),
        .w_v(cp_v), .w_row(cp_row), .w_m(cp_m), .w_d(cp_d), .fault(cap_f));
    wire wf_v; wire [13:0] wf_row; wire [511:0] wf_d; wire [3:0] wa_v; wire [55:0] wa_row; wire wfc_f;
    wire [7:0] x_rv; wire [4095:0] x_rd; wire [3:0] xa_v; wire [55:0] xa_row; wire xio_f; wire vm_fault;
    wire n_v; wire [83:0] n_d;
    wire [3:0] cl_v; wire [55:0] cl_row; wire [2047:0] cl_d; wire [63:0] cl_m; wire [31:0] cl_t;
    dsfd_vm_static_wfc #(.RLAT(13+READ_PIPE), .RESPONSE_PAD(3*READ_PIPE)) u_wfc (
        .ck_control_s(ck_wfc_control_s), .ck_control_t(ck_wfc_control_t), .ck_x34_s(ck_wfc_x34_s), .ck_x34_t(ck_wfc_x34_t),
        .ck_x43_s(ck_wfc_x43_s), .ck_x43_t(ck_wfc_x43_t), .rst_control_s(rst_wfc_control_s), .rss_control_t(rss_wfc_control_t),
        .rst_x34_s(rst_wfc_x34_s), .rss_x34_t(rss_wfc_x34_t), .rst_x43_s(rst_wfc_x43_s), .rss_x43_t(rss_wfc_x43_t), .f_wfc(f_wfc), .t_wfc(t_wfc),
        .w_v(wf_v), .w_row(wf_row), .w_d(wf_d), .a_v(wa_v), .a_row(wa_row), .e_v(x_rv[7:4]), .e_d(x_rd[4095:2048]),
        .vm_fault(vm_fault), .fault(wfc_f));
    dsfd_vm_static_xio #(.RLAT(13+READ_PIPE)) u_xio (
        .ck_control_s(ck_xio_control_s), .ck_control_t(ck_xio_control_t), .ck_x43_s(ck_xio_x43_s), .ck_x43_t(ck_xio_x43_t),
        .rst_control_s(rst_xio_control_s), .rss_control_t(rss_xio_control_t), .rst_x43_s(rst_xio_x43_s), .rss_x43_t(rss_xio_x43_t), .n_v(n_v), .n_d(n_d),
        .a_v(xa_v), .a_row(xa_row), .e_v(x_rv[3:0]), .e_d(x_rd[2047:0]),
        .f_collective(f_collective), .f_crq(f_crq), .t_crs(t_crs),
        .w_v(cl_v), .w_row(cl_row), .w_d(cl_d), .w_m(cl_m), .w_t(cl_t),
        .t_gather(t_gather), .f_xgo(f_xgo), .qSW(qSW), .qSWs(qSWs), .fault(xio_f));
    // edge faults -> engine 12 legacy-fault input (c_st[0]); serial levels registered once in the stream domain (seq tile)
    dsfd_vm_static_core #(.READ_PIPE(READ_PIPE)) u_core (.cks(ck_core_t), .rss(rss_core_t),
        .rst_rsched_n(rss_rsched_t), .rst_seq_n(rss_seq_t), .rst_landing_n(rss_landing_t),
        .rst_mem_fsr_n(rss_mem_fsr_t), .rst_mem_return_n(rss_mem_return_t), .rst_mem_bank_n(rss_mem_bank_t),
        .rst_mem_wcapture_n(rss_mem_wcapture_t), .rst_mem_wscatter_n(rss_mem_wscatter_t), .rst_mem_relay_n(rss_mem_relay_t),
        .rst_write_control_n(rss_write_control_t), .rst_write_header_n(rss_write_header_t), .rst_write_payload_n(rss_write_payload_t),
        .rst_write_dispatch_n(rss_write_dispatch_t), .rst_write_stage_n(rss_write_stage_t),
        .ck_read_data(ck_read_data_t), .ck_read_valid(ck_read_valid_t), .rst_read_data_n(rss_read_data_t), .rst_read_valid_n(rss_read_valid_t),
        .ck_rsched(ck_rsched_t), .ck_seq(ck_seq_t), .ck_landing(ck_landing_t),
        .ck_mem_fsr(ck_mem_fsr_t), .ck_mem_return(ck_mem_return_t), .ck_mem_bank(ck_mem_bank_t),
        .ck_mem_wcapture(ck_mem_wcapture_t), .ck_mem_wscatter(ck_mem_wscatter_t),
        .ck_mem_relay_req(ck_mem_relay_req_t), .ck_mem_relay_rsp(ck_mem_relay_rsp_t),
        .ck_write_control(ck_write_control_t), .ck_write_header(ck_write_header_t), .ck_write_payload(ck_write_payload_t),
        .ck_write_dispatch(ck_write_dispatch_t), .ck_write_stage(ck_write_stage_t), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .t_inp_su(t_inp_su[0]), .t_inp_hc(t_inp_hc[0]),
        .f_su_rqv(f_su_rqv), .f_su_rq(f_su_rq), .t_su_rsv(t_su_rsv), .t_su_rs(t_su_rs),
        .f_su_wqv(f_su_wqv), .f_su_wq(f_su_wq), .f_su_wqm(f_su_wqm), .f_su_wqd(f_su_wqd),
        .f_hc_rqv(f_hc_rqv), .f_hc_rq(f_hc_rq), .t_hc_rsv(t_hc_rsv), .t_hc_rs(t_hc_rs),
        .f_hc_wqv(f_hc_wqv), .f_hc_wq(f_hc_wq), .f_hc_wqm(f_hc_wqm), .f_hc_wqd(f_hc_wqd),
        .f_pqx(f_pqx), .t_pqx(t_pqx),
        .x_av({wa_v, xa_v}), .x_ar({wa_row, xa_row}), .x_rv(x_rv), .x_rd(x_rd), .nf_v(n_v), .nf_d(n_d),
        .f_mx_rqv(f_mx_rqv), .f_mx_rq(f_mx_rq), .t_mx_rsv(t_mx_rsv), .t_mx_rs(t_mx_rs),
        .f_mx_wqv(f_mx_wqv), .f_mx_wq(f_mx_wq), .f_mx_wqm(f_mx_wqm), .f_mx_wqd(f_mx_wqd),
        .l_v({xc_v, xs_v, xw_v, xw_v}), .l_d({xc_d[511:0], xs_d[511:0], xw_d[1023:512], xw_d[511:0]}),
        .cp_v(cp_v), .cp_row(cp_row), .cp_m(cp_m), .cp_d(cp_d), .cl_v(cl_v), .cl_row(cl_row), .cl_m(cl_m), .cl_d(cl_d), .cl_t(cl_t),
        .wf_v(wf_v), .wf_row(wf_row), .wf_d(wf_d),
        .x_al(x_al), .x_hdr({xw_v, xw_d[1025:1024], xc_v, xc_d[513:512], xs_v, xs_d[513:512]}),
        .edge_f({xio_f, wfc_f, cap_f}), .vm_fault(vm_fault));
endmodule
`default_nettype wire
