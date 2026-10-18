`timescale 1ns/1ps
// NATIVE-FIX3/kvhr (10-18): qkd_host_tx_class behind a local reset relay at the rst_n pin (HOST cluster child
// qkd_hr_core_tx). NATIVE-3 audit (claude/native-3-1017 73adc87ea) of the closed view qkd_hr_core_tx-r2-c372bf6fe:
// capture FAIL on the raw host_rst_n pin, 298.4 ps > 190 (the pin async-cleared ~650 tx flops across the tile).
// Now the pin drives only ot_rst_relay (2 sync flops + 1 kept relay flop); the relay output is the core reset.
// Assert stays asynchronous and immediate; RELEASE is 3 ck edges later than the pin (SYNC_STAGES 2 + TREE_STAGES 1).
// The core qkd_host_tx_class is unchanged (byte-identical file, every other binding untouched). The static schedule
// issues nothing to this child before 3 ck edges after host_rst_n release (documented in the kit structural_change).
// QKD_HR_RR_MUTANT (bench only): relay bypassed (raw pin = core reset) -> the release-latency bench FAILS.
module qkd_host_tx_class_rr #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire host_v,input wire[511:0]host_d,output wire host_cr,
 input wire ctrl_v,input wire[511:0]ctrl_d,output wire ctrl_cr,
 input wire ing_v,input wire[63:0]ing_d,output wire ing_cr,
 input wire[23:0]credit_return,peer_credit,input wire irq,
 output wire tx_v,output wire[527:0]tx_d,input wire tx_cr,
 output wire fault
);
 wire rst_q;
`ifdef QKD_HR_RR_MUTANT
 assign rst_q=rst_n;
`else
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rst_relay(.clk(ck),.rst_n_in(rst_n),.rst_n(rst_q));
`endif
 qkd_host_tx_class #(.MUT(MUT))u_tx(
  .ck(ck),.rst_n(rst_q),.host_v(host_v),.host_d(host_d),.host_cr(host_cr),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),
  .ctrl_cr(ctrl_cr),.ing_v(ing_v),.ing_d(ing_d),.ing_cr(ing_cr),.credit_return(credit_return),
  .peer_credit(peer_credit),.irq(irq),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(fault));
endmodule
