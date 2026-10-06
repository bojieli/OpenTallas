`timescale 1ps/1fs
// Bench-only result driver isolates NEW caller/receiver cones, NOT arithmetic.
module ot_hbm_item9_ha2_cached_map(input clk,rst_n,active,arm,input[7:0]rank,input[15:0]pf,
 input[1:0]h_v,input[1087:0]h_d,input[7:0]p_v,input[4359:0]p_flit,
 output reg r_v=0,output reg[15:0]r_m=0,output reg[511:0]r_d=0,
 output wire dupe,issue_o,quiet);
 assign dupe=0;assign issue_o=0;assign quiet=1;
endmodule
module tb_ha2_native_boundary_context;
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=0,go=0,rearm=1;reg[7:0]rank=19;reg[15:0]pf=384;
 reg[7:0]wv=0;reg[4359:0]wd=0;reg[1023:0]inj=0;
 wire[7:0]pop;wire fault;wire[4359:0]heads;wire[7:0]empty;
 ot_hbm_item9_ha2_native_boundary_context #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst_n),.go(go),.endpoint_rearm_ready(rearm),.rank(rank),.pf(pf),
 .context_operation(64'd123),.context_phase(32'd7),.inj_data(inj),
 .w2_v(wv),.w2_d(wd),.qr_pop(8'd0),.rb_pop(pop),.context_fault_o(fault),
 .qr_heads(heads),.qr_empty(empty));
 reg[511:0]payload;reg[544:0]result;
 initial begin
  repeat(3)@(negedge clk);rst_n=1;go=1;
  @(negedge clk);go=0;rearm=0;
  for(integer b=0;b<512;b=b+1)payload[b]=(b%13)<6;
  for(integer p=0;p<8;p=p+1)wd[p*545+:545]={1'b0,8'd19,8'(p),16'd0,payload};
  wv=255;@(posedge clk);#1;wv=0;
  if(pop!==255||fault)$fatal(1,"real eight head-read + dispatch");
  for(integer p=0;p<8;p=p+1)
   if(dut.g_on.partial_flit[p*545+:545]!==wd[p*545+:545])$fatal(1,"545b head mismatch");
  @(posedge clk);#1;if(pop!==0)$fatal(1,"head was not popped");
  @(negedge clk);
  dut.g_on.linked_child.u_owner.r_v=1;dut.g_on.linked_child.u_owner.r_m=16'd3;dut.g_on.linked_child.u_owner.r_d=payload;
  result={1'b1,8'hff,8'd2,16'd459,payload};
  @(posedge clk);#1;
  if(dut.g_on.u_dqo.mem[0]!==result||heads[0+:545]!==result||empty[0])$fatal(1,"real dqo/qr receiver writes");
  @(negedge clk);dut.g_on.linked_child.u_owner.r_v=0;
  if(!dut.g_on.own_pop||dut.g_on.dv==0)$fatal(1,"real own delivery dispatch");
  @(posedge clk);#1;
  @(negedge clk);wv=1;wd[0+:545]={1'b0,8'd18,8'd0,16'd0,payload};
  @(posedge clk);#1;wv=0;
  if(pop[0]||!dut.g_on.invalid_partial)$fatal(1,"foreign destination not refused before pop");
  @(posedge clk);#1;if(!fault)$fatal(1,"foreign destination fault not retained");
  $display("PASS native cones eight545b RX heads/dispatch, dqo+qr result writes, own delivery; foreign-dst refused+stickyfault. Arithmetic NOT exercised.");$finish;
 end
endmodule
