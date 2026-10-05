`timescale 1ns/1ps
module tb_window_stream_edges;
 reg clk=0;always #2 clk=~clk;
 reg rst_n=0,start=0,ready=1,fill=0,last=0;
 reg [20:0] row=0,first=126;
 reg [4:0] sector=0;reg [255:0] fd=0;
 reg [7:0] count=0;
 wire sr,rv,rr,sv,sfault,kv,done,fault;
 wire [9:0] ru,su;wire [20:0] rf,sf;
 wire [3:0] rm,sm,vm,km;wire [16895:0] rows;wire [16959:0] kw;
 integer cycle=0,accepted=0,accepted_total=0,max_reserved=0,checks=0;
 reg [16959:0] held;reg was_stalled=0;
 reg corrupt=0;wire [20:0] observed_first=sf^(corrupt?21'd1:21'd0);
 ot_chip_v41x_window_stage4 bank(.clk(clk),.rst_n(rst_n),.inv_v(1'b0),.inv_row(21'd0),.fill_v(fill),.fill_user(10'd0),.fill_row(row),.fill_sector(sector),.fill_data(fd),.fill_last(last),.req_v(rv),.req_ready(rr),.req_user(ru),.req_first_row(rf),.req_mask(rm),.rsp_v(sv),.rsp_user(su),.rsp_first_row(sf),.rsp_mask(sm),.rsp_valid_mask(vm),.rsp_rows(rows),.rsp_fault(sfault));
 ot_chip_v41x_window_stream dut(.clk(clk),.rst_n(rst_n),.start_v(start),.start_ready(sr),.start_user(10'd0),.start_first(first),.start_count(count),.req_v(rv),.req_ready(rr),.req_user(ru),.req_first(rf),.req_mask(rm),.rsp_v(sv),.rsp_user(su),.rsp_first(observed_first),.rsp_mask(sm),.rsp_valid_mask(vm),.rsp_rows(rows),.rsp_fault(sfault),.kv_v(kv),.kv_ready(ready),.kv_m(km),.kv_w(kw),.done(done),.fault(fault));
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(dut.reserved>4 || dut.received-dut.consumed>4) $fatal(1,"credit overflow");
  if(dut.reserved>max_reserved) max_reserved<=dut.reserved;
  if(kv)begin
   if(was_stalled&&held!==kw) $fatal(1,"unstable FIFO head");
   if(ready)begin
    for(integer l=0;l<4;l=l+1)begin
     if(km[l] !== (accepted*4+l<count)) $fatal(1,"bad final partial mask");
     if(km[l])for(integer g=0;g<16;g=g+1)
      if(kw[(l*16+g)*265+:265]!=={1'b0,8'd127,{32{8'(first+accepted*4+l)}}})$fatal(1,"wrong bank rotation/order");
    end
    accepted<=accepted+1;accepted_total<=accepted_total+1;
   end
  end
  was_stalled<=kv&&!ready;held<=kw;
 end
 task job(input integer n);
 begin
  while(!sr)@(negedge clk);
  count=n;accepted=0;start=1;@(negedge clk);start=0;
  // Stop after two requests: both bank pipeline stages can have replies pending.
  wait(dut.issued==2 || kv);@(negedge clk);ready=0;
  repeat(23)@(negedge clk);ready=1;
  wait(done);@(negedge clk);
  if(fault||accepted!=(n+3)/4)$fatal(1,"job count/fault");checks=checks+1;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(integer r=126;r<254;r=r+1)for(integer s=0;s<17;s=s+1)begin
   fill=1;row=r;sector=s;fd=(s==16)?{32{8'd127}}:{32{8'(r)}};last=(s==16);@(negedge clk);
  end
  fill=0;last=0;
  job(1);job(2);job(3);job(7);job(127);job(128);job(128);
  corrupt=1;count=8;start=1;@(negedge clk);start=0;
  wait(fault);if(kv)$fatal(1,"bad tagged response escaped");
  $display("STREAM_EDGES_PASS jobs=%0d accepted=%0d max_reserved=%0d partial=1 longstall=23 wrap=1 tagged_error=1",checks,accepted_total,max_reserved);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
