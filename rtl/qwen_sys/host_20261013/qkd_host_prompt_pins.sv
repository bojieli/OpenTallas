`timescale 1ns/1ps
// Actual8192x18 SECDED prompt backed by physical1024x256 masked SRAM.
// Request pins -> capture -> original encode/macro/decode -> response pin FF.
// q latency3edges after sampled request, fault4edges (originalsticky stage).
module qkd_host_prompt_pins #(parameter integer MUT=0)(
 input wire ck,rst_n,we,re,input wire[12:0]waddr,raddr,input wire[17:0]wdata,
 output reg[17:0]q,output reg fault
);
 reg we_q,re_q;reg[12:0]wa_q,ra_q;reg[17:0]wd_q;
 reg response_valid;wire[17:0]core_q;wire core_fault;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
  we_q<=0;re_q<=0;wa_q<=0;ra_q<=0;wd_q<=0;response_valid<=0;
 end else begin we_q<=we;re_q<=re;wa_q<=waddr;ra_q<=raddr;wd_q<=wdata;response_valid<=re_q;end
 ot_qfd_prompt_sram #(.MUT(MUT==3))u_core(.clk(ck),.rst_n(rst_n),.we(we_q),.re(re_q),
 .waddr(wa_q),.raddr(ra_q),.wdata(wd_q),.q(core_q),.fault(core_fault));
 always @(posedge ck or negedge rst_n)if(!rst_n)begin q<=0;fault<=0;end
 else begin
  if((MUT==2)?re_q:response_valid)q<=core_q ^ ((MUT==1)?18'd1:18'd0);
  fault<=core_fault;
 end
endmodule
