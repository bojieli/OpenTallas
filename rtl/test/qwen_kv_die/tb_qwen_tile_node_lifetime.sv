`timescale 1ns/1ps
// Real fixed node's input/valid/TOREG/reset implementation; arithmetic stub
// intentionally limits this fixture to event latency and metadata ownership.
module ot_qwen_w12_tadd #(parameter integer LAT=7,ANR=1)(input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
 assign y=0;assign fault=0;
endmodule
module tb_qwen_tile_node_lifetime;
 reg core_clk=0,rst_n=0,clear_context=0,node_va=0;
 reg [15:0] node_context=16'h1234,node_sequence=16'h5678;reg [31:0] node_version=32'h87654321;
 reg producer_seal_v=0;reg [15:0] producer_seal_context=16'h1234;reg [31:0] producer_seal_version=32'h87654321;
 reg node_retire_ack_toggle=0,node_accept_ack_toggle=0;
 wire node_credit,node_accept_credit,node_produced_toggle,node_accept_toggle,node_drained,fault;
 wire [63:0] node_produced_tuple,node_output_tuple,node_accept_tuple;
 wire node_output_valid;wire [47:0] node_active_identity;
 ot_qwen_tile_node_lifetime dut(.*);
 wire actual_vy;wire [511:0] actual_y,unused_tout;wire actual_fault,unused_tv;
 ot_qwen_tile_node real_node(.clk(core_clk),.rst_n(rst_n),.a(512'd0),.b(512'd0),.va(node_va),.y(actual_y),.vy(actual_vy),.fault(actual_fault),.t_d(512'd0),.t_vd(1'b0),.t_out(unused_tout),.t_vout(unused_tv));
 task step;begin #2;core_clk=1;#2;core_clk=0;#2;end endtask
 integer i;
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;repeat(16)step();
  node_va=1;step();node_va=0;
  if(node_accept_toggle!==1||node_accept_tuple!=={node_context,node_version,node_sequence})$fatal(1,"actual inputaccept metadata");
  node_accept_ack_toggle=node_accept_toggle;
  node_context=16'hffff;node_sequence=16'h9999;node_version=0;
  for(i=1;i<8;i=i+1)begin step();if(actual_vy||node_output_valid||node_produced_toggle)$fatal(1,"early nodeoutput at%0d",i);end
  step();
  if(!actual_vy||!node_output_valid||node_produced_toggle!==1||node_produced_tuple!==64'h1234876543215678||node_output_tuple!==node_produced_tuple)$fatal(1,"real9-capture-stage node mismatch");
  // Live producer changes offered descriptors during a complete coherent pause.
  node_context=16'hffff;node_sequence=16'h9999;node_version=0;
  #240;if(node_credit||node_drained||!actual_vy||node_produced_tuple!==64'h1234876543215678)$fatal(1,"paused outputownership");
  node_retire_ack_toggle=node_produced_toggle;step();
  if(actual_vy||node_output_valid||node_drained)$fatal(1,"outputretirement notdrain withoutseal");
  step();if(node_drained)$fatal(1,"premature certificate withoutproducerseal");
  producer_seal_v=1;step();producer_seal_v=0;step();
  if(!node_drained||fault||node_active_identity!==48'h123487654321)$fatal(1,"producerseal+retiredpipeline notdrained");
  clear_context=1;step();clear_context=0;if(node_drained)$fatal(1,"clear stale certificate");
  $display("PASS actual fixed-node9capture-stage metadata;240ns coherentpause;accept/produceseparate;retire+producerseal;fencedclear");$finish;
 end
endmodule
