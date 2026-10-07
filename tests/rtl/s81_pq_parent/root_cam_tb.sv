`timescale 1ns/1ps
module root_cam_tb;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0, i_v=0, i_e=0;
 reg [31:0] i_t=0,i_d=0;
 wire [1:0] rv,re,fault;
 wire [15:0] row[0:1],bf[0:1];
 wire [2:0] pos[0:1];
 wire [31:0] fp[0:1];
 ot_v41_ret_root #(.D(128),.QD(128)) native(
  .clk(clk),.rst_n(rst_n),.i_v(i_v),.i_t(i_t),.i_d(i_d),.i_e(i_e),
  .r_v(rv[0]),.r_row(row[0]),.r_pos(pos[0]),.r_fp32(fp[0]),.r_bf16(bf[0]),.r_e(re[0]),.fault(fault[0]));
 ot_s81_pq_ret_root_cam #(.D(128),.QD(128)) dut(
  .clk(clk),.rst_n(rst_n),.i_v(i_v),.i_t(i_t),.i_d(i_d),.i_e(i_e),
  .r_v(rv[1]),.r_row(row[1]),.r_pos(pos[1]),.r_fp32(fp[1]),.r_bf16(bf[1]),.r_e(re[1]),.fault(fault[1]));
 reg [51:0] seen[0:1][0:1023];
 reg valid[0:1][0:1023];
 integer publication_cycle[0:1][0:1023]; integer cycle=0;
 function [31:0] operand(input integer leaf);
 begin case(leaf)
 0:operand=32'h60ad78ec;1:operand=32'he0ad78ec;2:operand=32'h3f800000;3:operand=32'h3f800000;
 4:operand=0;5:operand=0;6:operand=0;default:operand=0;
 endcase end endfunction
 integer leaf;
 integer count[0:1]; integer k,j,n, mode=0;
 reg [1:0] queue_full_seen=0;
 integer full_buffer=0, simultaneous_update=0, queue_bypass=0, max_q=0;
 always @(posedge clk) begin
  cycle=cycle+1;
  if(rst_n && mode==2) begin
   if(native.qc==128)queue_full_seen[0]=1;
   if(dut.qc==128)queue_full_seen[1]=1;
  end
  if(rst_n && mode==0) begin
   if(dut.insert_b && dut.av) simultaneous_update=simultaneous_update+1;
   if(dut.use_q && dut.qc==1 && i_v) queue_bypass=queue_bypass+1;
   n=0;for(integer b=0;b<128;b=b+1)if(dut.bv[b])n=n+1;
   if(n==128)full_buffer=full_buffer+1;
   if(dut.qc>max_q)max_q=dut.qc;
  end
  #1;
  if(rst_n && mode==0) begin
   if(|fault)$fatal(1,"unexpected fault in bounded exact campaign");
   for(integer r=0;r<2;r=r+1)if(rv[r])begin
    if(row[r]>=1024 || valid[r][row[r]])$fatal(1,"duplicate/out-of-range row");
    publication_cycle[r][row[r]]=cycle;
    seen[r][row[r]]={pos[r],fp[r],bf[r],re[r]};
    valid[r][row[r]]=1;count[r]=count[r]+1;
   end
  end
 end
 task send(input integer r,input integer lo,input integer ns,input [31:0] data,input error);
 begin
  @(negedge clk);i_v=1;i_t={3'(r%8),16'(r),5'(lo),3'd0,5'(ns)};i_d=data;i_e=error;
 end endtask
 task idle(input integer cycles);
 begin @(negedge clk);i_v=0;repeat(cycles)@(negedge clk);end endtask
 task reset;
 begin @(negedge clk);rst_n=0;i_v=0;repeat(3)@(negedge clk);rst_n=1;end endtask
 initial begin
  count[0]=0;count[1]=0;
  for(k=0;k<1024;k=k+1)begin valid[0][k]=0;valid[1][k]=0;end
  reset();
  // Queue empty/singleton bypass and complete-candidate pipeline.
  for(k=0;k<160;k=k+1)send(k,0,1,32'h3f800000+k*65536+32'h8000,k%7==0);
  idle(20);
  // Adjacent siblings exercise same-edge insertion forwarding.
  for(k=160;k<224;k=k+1)begin
   send(k,1,2,32'h40000000,k%9==0);
   send(k,0,2,32'h3f800000,0);
   idle(2);
  end
  idle(40);
  // Occupy every CAM entry, then drain in reverse order.
  for(k=224;k<352;k=k+1)send(k,0,2,32'h3f800000,0);
  idle(5);
  for(k=351;k>=224;k=k-1)begin send(k,1,2,32'h40000000,k%13==0);idle(1);end
  idle(100);
  // Eight-leaf roots preserve canonical sibling tree despite arrival order.
  for(k=352;k<384;k=k+1)begin
   for(j=7;j>=0;j=j-1)begin
    leaf=(j&4)|((j&1)<<1)|((j&2)>>1);
    send(k,leaf,8,operand(leaf),leaf==3);
   end
   idle(24);
  end
  idle(200);
  if(count[0]!=384 || count[1]!=384)$fatal(1,"missing result native%0d cam%0d",count[0],count[1]);
  for(k=0;k<384;k=k+1)if(!valid[0][k] || !valid[1][k] || seen[0][k]!==seen[1][k])
   $fatal(1,"pairing/result mismatch row%0d ref%h got%h",k,seen[0][k],seen[1][k]);
  if(full_buffer==0 || simultaneous_update==0 || queue_bypass==0)$fatal(1,"hazard coverage missing");
  $display("LATENCY isolated complete delta%0d sibling delta%0d eightleaf delta%0d",publication_cycle[1][0]-publication_cycle[0][0],publication_cycle[1][160]-publication_cycle[0][160],publication_cycle[1][383]-publication_cycle[0][383]);
  // Native full-buffer sticky fault semantics, followed by reset recovery.
  mode=1;reset();
  for(k=0;k<129;k=k+1)send(k,0,2,32'h3f800000,0);
  idle(10);if(fault!==2'b11)$fatal(1,"buffer overflow fault lost");
  reset();idle(10);if(|fault || |rv)$fatal(1,"reset fault/publication leaked");
  // Force sustained adder-priority contention using real transactions until
  // each native-sized input queue reaches capacity and raises sticky fault.
  mode=2;
  for(k=0;k<2048;k=k+1)send((k/2)%512,k%2,2,32'h3f800000,0);
  idle(20);if(fault!==2'b11 || queue_full_seen!==2'b11)$fatal(1,"queue-pressure fault/coverage lost");
  reset();idle(10);if(|fault || |rv)$fatal(1,"final reset leaked");
  $display("PASS CAM384 exact roots, full128 buffer, insert-forward%0d queue-bypass%0d max_q%0d, overflow/reset",simultaneous_update,queue_bypass,max_q);
  $finish;
 end
 initial begin #200000;$fatal(1,"bounded stimulus failed to drain");end
endmodule
