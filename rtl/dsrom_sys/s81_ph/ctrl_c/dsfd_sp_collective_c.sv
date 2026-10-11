`timescale 1ns/1ps
// dsfd_sp_collective_c (s81-ctl-1011, 2026-10-11): the collective slab master with its coll engine endpoint
// (ADAPTER_CONTRACT_1011, engine 3; generator --ctrl-adapters).  = dsfd_sp_collective UNCHANGED behind
// ot_s81_coll_job on its VM input: f_vm lands in a pin flop, passes the job endpoint (records released only under a
// queued coll descriptor; +1 cycle) and enters the slab; t_vm is observed for the job's last result (done).
//   c<3> = {cv, cd 84} in (from dsfd_sp_ctrl / dsfd_sp_ctrl_e, controller clock c_ck), d<3> = {dv, dt 8} out,
//   cst = {online, fault} out (sticky; fault = wrong descriptor / protocol / endpoint fault).
// The slab clock / reset are the slab's own pll_stream / rst_stream (synchronised here for the endpoint).
module dsfd_sp_collective_c #(parameter integer JQ = 4, MUT = 0, EPMUT = 0) (
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
    input  wire [0:0]    c_ck, c_rs,
    input  wire [84:0]   c3,
    output wire [8:0]    d3,
    output wire [1:0]    cst
);
    wire ck = pll_stream[0];
    reg [1:0] rs_s;
    always @(posedge ck or negedge rst_stream[0]) if (!rst_stream[0]) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    reg [591:0] fv_q;
    always @(posedge ck or negedge rs_s[1]) if (!rs_s[1]) fv_q <= 592'd0; else fv_q <= f_vm;
    wire [591:0] core_f; wire jfault;
    ot_s81_coll_job #(.JQ(JQ), .MUT(MUT), .EPMUT(EPMUT)) u_job (.c_clk(c_ck[0]), .c_rst_n(c_rs[0]), .c_cmd(c3), .c_done(d3),
        .c_st(cst), .ck(ck), .rs_n(rs_s[1]), .vm_f(fv_q), .core_f(core_f), .core_t(t_vm), .fault(jfault));
    dsfd_sp_collective u_s (.refclk(refclk), .por(por), .f_vm(core_f), .ts(ts),
        .rW0(rW0), .rW1(rW1), .rW2(rW2), .rW3(rW3), .rE0(rE0), .rE1(rE1), .rE2(rE2), .rE3(rE3),
        .pll_stream(pll_stream), .pll_serial(pll_serial), .pll_hbm(pll_hbm),
        .rst_stream(rst_stream), .rst_serial(rst_serial), .rst_hbm(rst_hbm), .t_vm(t_vm),
        .tdW0(tdW0), .tdW1(tdW1), .tdW2(tdW2), .tdW3(tdW3), .tdE0(tdE0), .tdE1(tdE1), .tdE2(tdE2), .tdE3(tdE3),
        .tfW0(tfW0), .tfW1(tfW1), .tfW2(tfW2), .tfW3(tfW3), .tfE0(tfE0), .tfE1(tfE1), .tfE2(tfE2), .tfE3(tfE3));
endmodule
