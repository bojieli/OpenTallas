`timescale 1ns/1ps
// NATIVE-FIX3/kvhr (10-18): qkd_host_rx_class_admission behind a local reset relay at the rst_n pin (HOST cluster
// direct child qkd_hr_core_rx). NATIVE-3 audit (claude/native-3-1017 73adc87ea) of the closed view
// hr_core_rx-b1-161e15878: capture FAIL on the raw rst_n pin, 256.6 ps > 190 (the pin async-cleared every rx flop).
// Now the pin drives only ot_rst_relay (2 sync flops + 1 kept relay flop); the relay output is the core reset.
// Assert stays asynchronous and immediate; RELEASE is 3 ck edges later than the pin (SYNC_STAGES 2 + TREE_STAGES 1).
// The core qkd_host_rx_class_admission (+ qkd_host_rx_class) is unchanged (byte-identical files). The static schedule
// issues nothing to this child before 3 ck edges after host_rst_n release (documented in the kit structural_change).
// QKD_HR_RR_MUTANT (bench only): relay bypassed (raw pin = core reset) -> the release-latency bench FAILS.
module qkd_host_rx_class_admission_rr #(parameter integer MUT=0,STRAPPED=0,IR_REPL=0)(
 input wire ck,rst_n,input wire[2:0]die_id,input wire rx_v,input wire[527:0]rx_d,output wire rx_cr,
 input wire native_reserved,ownership_valid,
 output wire host_v,output wire[511:0]host_d,input wire host_cr,
 output wire ctrl_v,output wire[511:0]ctrl_d,input wire ctrl_cr,
 output wire ing_v,output wire[1:0]ing_cls,output wire[511:0]ing_d,input wire[4:0]ing_crn,
 output wire[23:0]credit_return,peer_credit,output wire fault,
 output wire admission_open,launch_quiet,output wire deferred
);
 wire rst_q;
`ifdef QKD_HR_RR_MUTANT
 assign rst_q=rst_n;
`else
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rst_relay(.clk(ck),.rst_n_in(rst_n),.rst_n(rst_q));
`endif
 qkd_host_rx_class_admission #(.MUT(MUT),.STRAPPED(STRAPPED),.IR_REPL(IR_REPL))u_adm(
  .ck(ck),.rst_n(rst_q),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
  .native_reserved(native_reserved),.ownership_valid(ownership_valid),
  .host_v(host_v),.host_d(host_d),.host_cr(host_cr),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(ctrl_cr),
  .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),
  .credit_return(credit_return),.peer_credit(peer_credit),.fault(fault),
  .admission_open(admission_open),.launch_quiet(launch_quiet),.deferred(deferred));
endmodule
