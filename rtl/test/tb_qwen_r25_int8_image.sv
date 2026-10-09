`timescale 1ns/1ps
// Minimum actual issuer+unpacker geometry with group-slot padded wave.
module tb_qwen_r25_int8_image;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start_v=0;
 wire launch,w_valid,w_ready,iss_v,row_ok,line_end;
 wire [11:0] row;wire [6:0] xa;
 wire [1087:0] out_data;
 reg [1087:0] image[0:23];reg [15:0] canonical[0:3071];
 wire raw_ready;
 reg input_open=0;
 integer line_no=0,seen=0,lane,index,cycles=0;
 always @(posedge clk) if(!rst_n) input_open<=0;
 else if(launch) input_open<=1;else if(line_end) input_open<=0;
 wire demand=input_open&&!line_end;
 wire source_valid=line_no<24 && cycles%5!=2;
 ot_hbm_accel_int8_line unpack(.clk(clk),.rst_n(rst_n),.int8_mode(1'b1),
  .s_valid(source_valid&&demand),.s_ready(raw_ready),.s_data(image[line_no<24?line_no:0]),
  .m_valid(w_valid),.m_ready(w_ready),.m_data(out_data));
 ot_hbm_accel_issue_pq #(.IL(8),.RMAX(4096),.XDEPTH(128)) issue(
  .clk(clk),.rst_n(rst_n),.start_v(start_v),.launch(launch),.op_rows(13'd3),
  .op_c(16'd8),.op_g(8'd2),.op_gs(1'b1),.op_bf(1'b1),.w_valid(w_valid),
  .x_rdy(1'b1),.w_ready(w_ready),.rdone(1'b0),.release_in(1'b0),
  .iss_v(iss_v),.iss_row_ok(row_ok),.iss_line_end(line_end),.iss_row(row),.xa(xa));
 always @(posedge clk) if(rst_n) begin
  cycles=cycles+1;
  if(source_valid&&demand&&raw_ready) line_no<=line_no+1;
  if(iss_v&&row_ok) begin
   for(lane=0;lane<64;lane=lane+1) begin
    // xa = group*8 + t; BF16 ring lane has strided canonical column.
    index=row*1024+((xa/8)*64+lane)*8+(xa%8);
    if(out_data[lane*16+:16]!==canonical[index])
     $fatal(1,"canonical operand mismatch row %0d xa %0d lane %0d",row,xa,lane);
   end
   if(out_data[1087:1024]!==0) $fatal(1,"fmt3 sidecar nonzero");
   seen=seen+1;
  end
 end
 initial begin
  $readmemh("image.hex",image);$readmemh("canonical.hex",canonical);
  repeat(3) @(negedge clk);rst_n=1;start_v=1;
  while(!launch) @(negedge clk);
  @(negedge clk);start_v=0;
  while(seen<48) @(negedge clk);
  repeat(20) @(negedge clk);
  if(line_no!=24||w_valid) $fatal(1,"ghost packed line");
  $display("PASS canonical INT8 image consumed by production IL8 group-slot issuer; real beats=%0d packed lines=%0d cycles=%0d",seen,line_no,cycles);$finish;
 end
 initial begin #100000;$fatal(1,"deadlock watchdog");end
endmodule
