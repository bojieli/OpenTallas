`timescale 1ns/1ps
module tb_hbm_int8_issue;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start_v=0,op_bf=1,mode=0;
 reg [12:0] op_rows=3;reg [15:0] op_c=2;
 wire launch,w_valid,w_ready,iss_v,row_ok,line_end;
 wire [1087:0] out_data;reg [1087:0] data;
 wire source_ready,raw_ready;
 reg input_open=0;
 always @(posedge clk) if(!rst_n) input_open<=0;
 else if(launch) input_open<=1;else if(line_end) input_open<=0;
`ifdef OT_INT8_MUT_PREFETCH
 wire demand=input_open; // removes last-real-beat gate: must prefetch the wrong format
`else
 wire demand=input_open&&!line_end;
`endif
 integer line_no=0,seen=0,k,code,cycles=0;
 reg [15:0] golden[0:255];
 initial $readmemh("golden.hex",golden);
 always_comb begin
  data=0;
  for(integer i=0;i<136;i=i+1) data[8*i+:8]=(line_no*128+i)%256;
 end
 assign source_ready=raw_ready&&demand;
 ot_hbm_accel_int8_line unpack(.clk(clk),.rst_n(rst_n),.int8_mode(mode),
  .s_valid(demand),.s_ready(raw_ready),.s_data(data),
  .m_valid(w_valid),.m_ready(w_ready),.m_data(out_data));
 ot_hbm_accel_issue_pq #(.IL(8),.RMAX(4096),.XDEPTH(128),.HAZ(1)) issue(
  .clk(clk),.rst_n(rst_n),.start_v(start_v),.launch(launch),.op_rows(op_rows),
  .op_c(op_c),.op_g(8'd1),.op_gs(1'b0),.op_bf(op_bf),.w_valid(w_valid),
  .x_rdy(1'b1),.w_ready(w_ready),.rdone(1'b0),.release_in(1'b0),
  .iss_v(iss_v),.iss_row_ok(row_ok),.iss_line_end(line_end));
 always @(posedge clk) if(rst_n) begin
  cycles=cycles+1;
  if(source_ready) begin line_no<=line_no+1;end
  if(iss_v&&row_ok) begin
   if(seen<6) begin
    for(k=0;k<64;k=k+1) begin
     code=(seen*64+k)%256;
     if(out_data[k*16+:16]!==golden[code]) $fatal(1,"fmt3 issued beat mismatch %0d lane %0d got %h expected %h",seen,k,out_data[k*16+:16],golden[code]);
    end
   end else begin
    for(k=0;k<136;k=k+1)
     if(out_data[k*8+:8]!==((seen-3)*128+k)%256) $fatal(1,"legacy issued mismatch %0d lane %0d",seen,k);
   end
   seen=seen+1;
  end
 end
 initial begin
  repeat(3) @(negedge clk);rst_n=1;start_v=1;
  while(!launch) @(negedge clk);
  @(negedge clk);start_v=0;mode=1;
  while(seen<6) @(negedge clk);
  // Padded slots must consume no extra source line from the next operation.
  repeat(3) @(negedge clk);
  if(line_no!=3) $fatal(1,"cross-operation prefetch: %0d lines",line_no);
  op_rows=2;op_bf=0;start_v=1;
  while(!launch) @(negedge clk);
  @(negedge clk);start_v=0;mode=0;
  while(seen<10) @(negedge clk);
  repeat(20) @(negedge clk);
  if(line_no!=7||w_valid) $fatal(1,"extra line/beat %0d",line_no);
  $display("PASS production IL8 issue, padded rows, fmt3->legacy operation transition; beats=%0d lines=%0d cycles=%0d",seen,line_no,cycles);$finish;
 end
 initial begin #100000;$fatal(1,"deadlock watchdog");end
endmodule
