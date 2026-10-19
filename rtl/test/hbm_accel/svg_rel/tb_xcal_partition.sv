`timescale 1ns/1ps
module tb_xcal_partition;
 parameter integer MUT=0;
 parameter integer EARLY=0;
 parameter integer MULTI=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[7:0]tgt=8'hc0,cfg_target=8'hc0;reg cfg_v=0,desc_v=0,launch_v=0;
 reg[11:0]cfg_addr=0,desc_base=255;reg[255:0]cfg_data=0;reg[12:0]desc_limit=256;reg[15:0]desc_loops=1;
 wire[108:0]cmd_ext;wire[63:0]kv_desc;wire done,configured,fault,active;
 integer edges=0,launch_edge=0,seen=0,errors=0,first_edge=-1,i;reg[255:0]data;
 ot_hbm_xcal_partition_t #(.MUT(MUT)) dut(.clk_desc(clk),.clk_prog(clk),.*);
 always @(posedge clk)begin
  edges=edges+1;if(launch_v)launch_edge=edges;
  #1;
  if(cmd_ext!==0 && rst_n && launch_edge>0)begin
   if(first_edge<0)first_edge=edges;
   if(cmd_ext!==109'(17+(seen%4))||kv_desc!==64'(64+(seen%4)))errors=errors+1;
   if(edges!=launch_edge+29+(seen%4)+(seen/4)*12)errors=errors+1;
   seen=seen+1;
  end
 end
 task idle;input integer n;begin repeat(n)@(negedge clk);end endtask
 task wr;input[7:0]id;input[11:0]a;input[255:0]v;begin @(negedge clk);cfg_target=id;cfg_addr=a;cfg_data=v;cfg_v=1;@(negedge clk);cfg_v=0;idle(4);end endtask
 initial begin
  idle(3);rst_n=1;idle(8);if(MULTI)desc_base=254;
  for(i=0;i<4;i=i+1)begin
   data=0;data[255:240]=16'hc7a1;data[234:224]=11'(1024+i);data[108:0]=109'(17+i);data[172:109]=64'(64+i);
   wr(8'hc0,12'(12'h800+i),data);
  end
  data=0;data[255:240]=16'hc7a1;data[234:224]=1024;data[108:0]=999;
  wr(8'hc1,12'h800,data); // wrong target must not overwrite programme
  data=0;data[255:240]=16'h5d15;data[239:232]=255;data[189]=1;data[102:92]=1028;data[118:103]=1;data[142:119]=EARLY ? 1 : 20;
  if(MULTI) begin
   data[239:232]=254;wr(8'hc0,12'h4fe,data);data[239:232]=255;data[142:119]=32;
  end
  wr(8'hc0,12'h4ff,data);
  @(negedge clk);desc_v=1;@(negedge clk);desc_v=0;idle(4);
  if(!configured)errors=errors+1;
  @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;idle(80);
  if(EARLY)begin if(seen!=0||!fault)errors=errors+1;end
  else if(seen!=(MULTI?8:4)||fault)errors=errors+1;
  $display("XCAL_PARTITION %s mut=%0d errors=%0d words=%0d first_delta=%0d fault=%0d",errors==0?"PASS":"FAIL",MUT,errors,seen,first_edge-launch_edge,fault);
  if(errors)$fatal(1,"XCAL relative mismatch");$finish;
 end
endmodule
