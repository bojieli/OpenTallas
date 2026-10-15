`timescale 1ns/1ps
// dsfd_sp_collective_c (s81-ctl-1011, 2026-10-11): the collective slab master WITH its coll engine endpoint
// (ADAPTER_CONTRACT_1011, engine 3; generator --ctrl-adapters) = dsfd_sp_collective compiled with +define+OT_S81PH_COLL_JOB
// (split3cr: ot_s81_coll_job inside dsfd_coll_cb between the f_vm pin register and the seam register, +0 cycles; v2 core:
// the dsfd_coll_job tile in front of the core, +1 on f_vm).  Records of a coll message reach the engine only under the
// message's descriptor; the done is the message's last result leaving the slab (t_vm header at the slab's VM-edge flops).
//   c_cmd = c<3> = {cv, cd 84} in, c_done = d<3> = {dv, dt 8} out, c_st = s<3> = {online, fault} out (sticky), all on
//   the die stream clock (pll_stream, this slab's clock = the sequencer's).
// s81-die-rtl-bind 2026-10-14 (F2): the slab's VM interface passes through the adapter tile dsfd_coll_xc
// (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_xc.sv): HC y bus, WFC kit link (stage hop on a pass-through channel) and the
// layer-die host channel; +1 cycle on f_vm / ts / t_vm.
`ifndef OT_S81PH_COLL_JOB
`define OT_S81PH_COLL_JOB_MISSING
`endif
module dsfd_sp_collective_c (
    input  wire [0:0]    refclk,
    input  wire [0:0]    por,
    input  wire [591:0]  f_vm,
    input  wire [2:0]    ts,
    input  wire [514:0]  rW0, rW1, rW2, rW3, rE0, rE1, rE2, rE3,
    output wire [0:0]    pll_stream, pll_serial, pll_hbm,
    output wire [0:0]    rst_stream, rst_serial, rst_hbm,
    output wire [2099:0] t_vm,
    output wire [511:0]  tdW0, tdW1, tdW2, tdW3, tdE0, tdE1, tdE2, tdE3,
    output wire [0:0]    tfW0, tfW1, tfW2, tfW3, tfE0, tfE1, tfE2, tfE3,
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st,
    // s81-die-rtl-bind 2026-10-14 (F2): the die clients of the collective (adapter tile dsfd_coll_xc on the VM interface)
    output wire [8191:0] t_hc_y,               // HC y bus (16 all-reduce words a beat), valid / ready
    output wire [0:0]    t_hc_yv,
    input  wire [0:0]    f_hc_yr,
    output wire [513:0]  t_wfc,                // WFC kit link in  {last, data 512, valid}; f_wfcg = the kit's grant
    input  wire [0:0]    f_wfcg,
    input  wire [513:0]  f_wfc,                // WFC kit link out {last, data 512, valid}; t_wfcg = this end's grant
    output wire [0:0]    t_wfcg,
    output wire [515:0]  t_host,               // host channel in  {t_cr, h_cls 2, h_d 512, h_v} (dsfd_host_c f_collective)
    input  wire [80:0]   f_host                // host channel out {st 11, h_crn 5, t_v, t_d 64} (dsfd_host_c t_collective)
);
`ifdef OT_S81PH_COLL_JOB_MISSING
    initial $fatal(1, "dsfd_sp_collective_c: compile with +define+OT_S81PH_COLL_JOB (the coll endpoint inside the slab)");
`else
    wire [591:0] c_fvm; wire [2:0] c_ts; wire [2099:0] c_tvm;
    dsfd_sp_collective u_s (.refclk(refclk), .por(por), .f_vm(c_fvm), .ts(c_ts),
        .rW0(rW0), .rW1(rW1), .rW2(rW2), .rW3(rW3), .rE0(rE0), .rE1(rE1), .rE2(rE2), .rE3(rE3),
        .pll_stream(pll_stream), .pll_serial(pll_serial), .pll_hbm(pll_hbm),
        .rst_stream(rst_stream), .rst_serial(rst_serial), .rst_hbm(rst_hbm), .t_vm(c_tvm),
        .tdW0(tdW0), .tdW1(tdW1), .tdW2(tdW2), .tdW3(tdW3), .tdE0(tdE0), .tdE1(tdE1), .tdE2(tdE2), .tdE3(tdE3),
        .tfW0(tfW0), .tfW1(tfW1), .tfW2(tfW2), .tfW3(tfW3), .tfE0(tfE0), .tfE1(tfE1), .tfE2(tfE2), .tfE3(tfE3),
        .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
    dsfd_coll_xc #(.MUT(`ifdef OT_COLLXC_MUT `OT_COLLXC_MUT `else 0 `endif)) u_xc (.ck(pll_stream), .rst(rst_stream),
        .f_vm(f_vm), .ts(ts), .t_vm(t_vm), .c_fvm(c_fvm), .c_ts(c_ts), .c_tvm(c_tvm),
        .t_hc_y(t_hc_y), .t_hc_yv(t_hc_yv), .f_hc_yr(f_hc_yr), .t_wfc(t_wfc), .f_wfcg(f_wfcg), .f_wfc(f_wfc),
        .t_wfcg(t_wfcg), .t_host(t_host), .f_host(f_host));
`endif
endmodule
