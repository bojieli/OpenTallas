`timescale 1ns/1ps
// Opt-in native assembly: the actual HC queue owns transfer readiness.
// Package writes tee to landing, while original writes still commit in VM.
// commit_* is the VM's acknowledged full-row commit, never the HC wq issue.
// The existing native HC die wrapper uses one stream clock for both adapter
// sides. A serial-clock composition must supply qualified CDC boundaries.
// Assigned physical pins, current-source full arithmetic and a deployed
// program remain required before this assembly is adopted.
module dsfd_sp_hc_transfer_c #(
 parameter integer NG=256,D=5120,S_RD=2,S_WR=8,S_RT=4,
 parameter integer RXB=0,TXB=6144,XW=640,PIPE=0,PIPE_PD=40,
 parameter integer TFW=(72+16*S_RD)+((S_RD*512>((NG/8+2)/3)*8*32)?S_RD*512:((NG/8+2)/3)*8*32)+S_RD+5+129,
 parameter integer TRW=S_RT+24*S_RT+8+512*S_RT+S_RT+4
)(
 input wire ck,rst,
 input wire [84:0] c_cmd,output wire [8:0] c_done,output wire [1:0] c_st,
 input wire normal_inputs_present,
 input wire package_vm_we,input wire [13:0] package_vm_addr,input wire [511:0] package_vm_data,
 input wire y_v,output wire y_rdy,input wire [NG*32-1:0] y_d,
 output wire [S_RD-1:0] vm_rq_v,output wire [S_RD*14-1:0] vm_rq_row,
 input wire [S_RD-1:0] vm_rs_v,input wire [S_RD*512-1:0] vm_rs_d,
 output wire [S_WR-1:0] wq_v,output wire [S_WR*14-1:0] wq_row,
 output wire [S_WR*16-1:0] wq_mask,output wire [S_WR*512-1:0] wq_d,
 input wire [S_WR-1:0] commit_v,input wire [S_WR*14-1:0] commit_a,input wire [S_WR*16-1:0] commit_mask,
 output wire hop_go,input wire hop_re,input wire [13:0] hop_ra,
 output wire hop_vm_re,output wire [13:0] hop_vm_ra,
 output wire [85:0] head_snapshot,
 output wire [TFW-1:0] t_tf0,t_tf1,t_tf2,input wire [TRW-1:0] f_tr0,f_tr1,f_tr2,
 output wire transfer_fault,output wire [3:0] transfer_fault_code
);
 initial if(NG!=256 || D!=5120 || S_RD!=2 || S_WR!=8 || S_RT!=4 || XW!=640)
   $fatal(1,"native HC assembly requires the actual production tuple");
 wire inp;wire [S_RD-1:0] hc_rq_v,hc_rs_v;
 wire [S_RD*14-1:0] hc_rq_row;wire [S_RD*512-1:0] hc_rs_d;
 dsfd_sp_hc_c #(.NG(NG),.D(D),.S_RD(S_RD),.S_WR(S_WR),.S_RT(S_RT),
 .HIER(1),.HALF(1),.CSPLIT(1),.TAIL_SPLIT(2),.CNL_PIN(1),.CHAIN_STEP(6),
 .HEAD_ROWS(10),.LANE_SPECIALIZE(1),.PIPE(PIPE),.PIPE_PD(PIPE_PD)) hc(
 .ck(ck),.rst(rst),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),.f_inp(inp),.t_head(head_snapshot),
 .y_v(y_v),.y_rdy(y_rdy),.y_d(y_d),.rq_v(hc_rq_v),.rq_row(hc_rq_row),.rs_v(hc_rs_v),.rs_d(hc_rs_d),
 .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),
 .t_tf0(t_tf0),.t_tf1(t_tf1),.t_tf2(t_tf2),.f_tr0(f_tr0),.f_tr1(f_tr1),.f_tr2(f_tr2));
 ot_s81_htransfer_boundary #(.RXB(RXB),.TXB(TXB),.XW(XW),.S_RD(S_RD),.S_WR(S_WR)) boundary(
 .clk(ck),.rst_n(rst),.land_v(package_vm_we),.land_a(package_vm_addr),.land_d(package_vm_data),
 .hc_head(head_snapshot),.normal_inputs_present(normal_inputs_present),.hc_inputs_present(inp),
 .hc_rq_v(hc_rq_v),.hc_rq_row(hc_rq_row),.hc_rs_v(hc_rs_v),.hc_rs_d(hc_rs_d),
 .vm_rq_v(vm_rq_v),.vm_rq_row(vm_rq_row),.vm_rs_v(vm_rs_v),.vm_rs_d(vm_rs_d),
 .commit_v(commit_v),.commit_a(commit_a),.commit_mask(commit_mask),.hop_go(hop_go),
 .hop_re(hop_re),.hop_ra(hop_ra),.hop_vm_re(hop_vm_re),.hop_vm_ra(hop_vm_ra),
 .fault(transfer_fault),.fault_code(transfer_fault_code));
endmodule
