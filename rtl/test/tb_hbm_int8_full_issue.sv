`timescale 1ns/1ps
module tb_hbm_int8_full_issue #(parameter integer PIPE=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start_v=0,input_open=0;
 reg [12:0] rows=3;reg [7:0] groups=2;
 wire launch,line_end,credit,raw_ready,source_ready,v,ready,iss_v,row_ok;
 wire [1087:0] data;
 integer nr,ng,seen=0,lines=0,cycles=0;
 initial begin
  if(!$value$plusargs("ROWS=%d",nr)) nr=3;
  if(!$value$plusargs("GROUPS=%d",ng)) ng=2;
  rows=nr;groups=ng;
 end
 always @(posedge clk) if(!rst_n) input_open<=0;
 else if(launch) input_open<=1;else if(line_end) input_open<=0;
 generate if(PIPE) begin
  ot_hbm_accel_int8_credit #(.RW(12)) counter(.clk(clk),.rst_n(rst_n),.launch(launch),
   .take(source_ready),.int8_mode(1'b1),.op_rows(rows),.op_g(groups),.op_c(16'd8),.intake_credit(credit));
 end else assign credit=1;endgenerate
 wire demand=input_open&&!line_end&&credit;
 assign source_ready=raw_ready&&demand;
 ot_hbm_accel_int8_line #(.PIPE(PIPE)) unpack(.clk(clk),.rst_n(rst_n),.int8_mode(1'b1),
  .s_valid(demand),.s_ready(raw_ready),.s_data(1088'd0),.m_valid(v),.m_ready(ready),.m_data(data));
 ot_hbm_accel_issue_pq #(.IL(8),.RMAX(4096),.XDEPTH(4096),.HAZ(1)) issuer(
  .clk(clk),.rst_n(rst_n),.start_v(start_v),.launch(launch),.op_rows(rows),.op_c(16'd8),
  .op_g(groups),.op_gs(1'b1),.op_bf(1'b1),.w_valid(v),.w_ready(ready),.x_rdy(1'b1),
  .rdone(1'b0),.release_in(1'b0),.iss_v(iss_v),.iss_row_ok(row_ok),.iss_line_end(line_end));
 always @(posedge clk) if(rst_n) begin
  cycles=cycles+1;
  if(source_ready) lines=lines+1;
  if(iss_v&&row_ok) begin
   if(data!==1088'd0) $fatal(1,"zero canonical operand mismatch");
   seen=seen+1;
  end
 end
 initial begin
  repeat(3) @(negedge clk);rst_n=1;start_v=1;
  while(!launch) @(negedge clk);
  @(negedge clk);start_v=0;
  while(seen<nr*ng*8) @(negedge clk);
  repeat(20) @(negedge clk);
  if(lines!=nr*ng*4||v) $fatal(1,"prefetched past full operation: lines=%0d",lines);
  $display("PASS full issuer rows=%0d groups=%0d pipe=%0d beats=%0d lines=%0d cycles=%0d",nr,ng,PIPE,seen,lines,cycles);$finish;
 end
 initial begin #20000000;$fatal(1,"deadlock watchdog");end
endmodule
