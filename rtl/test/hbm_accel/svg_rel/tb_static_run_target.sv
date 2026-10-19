`timescale 1ns/1ps
module tb_static_run_target;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;reg [7:0]tgt=8'h40,cfg_target=8'h40;
 reg cfg_v=0,desc_v=0,launch_v=0;reg[11:0]cfg_addr=0,desc_base=0;
 reg[255:0]cfg_data=0;reg[12:0]desc_limit=0;reg[15:0]desc_loops=1;
 wire a_we,b_we,run_v,configured,fault,active;wire[10:0]a_addr;wire[7:0]b_addr,run_base,run_arg;
 wire[8:0]run_count;wire[255:0]a_data,b_data;
 integer errors=0,aw=0,bw=0,runs=0,edge_no=0,launched_at=0;
 ot_static_run_target #(.AWA(11),.AWB(8),.RBW(8),.RCW(9),.NA(2),.NF(1),.RSYNC(1),.MUT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(2'b0),.tgt_fault(1'b0),.a_we(a_we),.a_addr(a_addr),.a_data(a_data),.b_we(b_we),.b_addr(b_addr),.b_data(b_data),
 .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_arg(run_arg),.configured(configured),.fault(fault),.active(active));
 always @(posedge clk)begin
  edge_no=edge_no+1;if(launch_v)launched_at=edge_no;
  #1;
  if(a_we)begin aw=aw+1;if(a_addr!==11'd1031||a_data!==256'hdeadbeef)errors=errors+1;end
  if(b_we)begin bw=bw+1;if(b_addr!==8'd255||b_data!==256'h01234567)errors=errors+1;end
  if(run_v)begin runs=runs+1;if(run_base!==8'd240||run_count!==9'd16||run_arg!==8'd14||edge_no!=launched_at+1)errors=errors+1;end
 end
 task idle;input integer n;begin repeat(n)@(negedge clk);end endtask
 task wr;input[7:0]id;input[11:0]a;input[255:0]v;begin @(negedge clk);cfg_target=id;cfg_addr=a;cfg_data=v;cfg_v=1;@(negedge clk);cfg_v=0;idle(3);end endtask
 initial begin
  idle(3);rst_n=1;idle(6);
  wr(8'h41,12'h807,256'hdeadbeef); // other target must not write
  wr(8'h40,12'h807,256'hdeadbeef); // programme row 1024+7 through window2
  wr(8'h40,12'h4ff,256'h01234567); // descriptor row255
  @(negedge clk);cfg_target=8'h40;desc_base=240;desc_limit=256;desc_loops=15;desc_v=1;
  @(negedge clk);desc_v=0;idle(3);
  if(!configured)errors=errors+1;
  @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;idle(4);
  // An armed descriptor is consumed once. A second launch faults and must not rerun.
  @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;idle(4);
  if(aw!=1||bw!=1||runs!=1||!fault)errors=errors+1;
  $display("RUN_TARGET %s mut=%0d errors=%0d programme=%0d descriptor=%0d runs=%0d",errors==0?"PASS":"FAIL",MUT,errors,aw,bw,runs);
  if(errors)$fatal(1,"run target mismatch");$finish;
 end
endmodule
