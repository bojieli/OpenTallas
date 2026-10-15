`timescale 1ns/1ps
// Real stage source resource fact affects integrity only, never the start edge.
module tb_qwen_stage_resource_gate;
 parameter integer REQUIRES=0;
 reg ck=0;always #1 ck=~ck;
 reg rn=0,start=0;wire go,fault,tok;wire[17:0]gt,gp;wire[5:0]st;
 integer edges=0;
 ot_qfd_stage_gate_static dut(.clk(ck),.rst_n(rn),.h_start(start),.stage(6'd0),.token(18'd151935),.pos(18'd8191),
 .requires_cbuf(REQUIRES!=0),.st_rdy(1'b0),.st_rdy_stage(6'd0),.go(go),.go_token(gt),.go_pos(gp),.cur_stage(st),.tok_start(tok),.fault(fault));
 always @(posedge ck)if(go)begin
  edges=edges+1;
  if(gt!=151935||gp!=8191||st!=0)$fatal(1,"accepted source context changed");
 end
 initial begin
 repeat(3)@(negedge ck);rn=1;repeat(2)@(negedge ck);start=1;
 @(negedge ck);start=0;@(negedge ck);
 if(edges!=1||fault!==(REQUIRES!=0))$fatal(1,"resource requirement changed fixed launch or false fault edges%0d fault%b",edges,fault);
 $display("PASS source resource requirement%0d fixed launch with cold CBUF fault%b",REQUIRES,fault);$finish;
 end
endmodule
