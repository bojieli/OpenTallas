`timescale 1ns/1ps
// Genuine original reset checker behind registered status pins. POR remains
// asynchronous to the original synchronizer; every release output is its flop.
module qkd_host_rst_pins #(parameter NL=6,ND=8,T_LINK=200000,T_HBM=200000)(
 input wire clk,por_n,soft_rst,input wire[NL-1:0]link_up,
 input wire[ND-1:0]boot_done,boot_ok,
 output wire host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,boot_fault,
 output wire[3:0]boot_state,boot_err,output wire[31:0]boot_cycles
);
 reg soft_q;reg[NL-1:0]links_q;reg[ND-1:0]done_q,ok_q;
 always @(posedge clk or negedge por_n)if(!por_n)begin soft_q<=0;links_q<=0;done_q<=0;ok_q<=0;end
 else begin soft_q<=soft_rst;links_q<=link_up;done_q<=boot_done;ok_q<=boot_ok;end
 ot_qwen_sys_rst_seq #(.NL(NL),.ND(ND),.T_LINK(T_LINK),.T_HBM(T_HBM)) u_core(
 .clk(clk),.por_n(por_n),.soft_rst(soft_q),.link_up(links_q),.boot_done(done_q),.boot_ok(ok_q),
 .host_rst_n(host_rst_n),.link_rst_n(link_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),
 .die_rst_n(die_rst_n),.sys_ready(sys_ready),.boot_fault(boot_fault),.boot_state(boot_state),.boot_err(boot_err),.boot_cycles(boot_cycles));
endmodule
