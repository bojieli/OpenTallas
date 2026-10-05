`timescale 1ns/1ps
// PARENT-REVIEWED COMPILE ONLY: full128-lane actual arithmetic, no blackboxes.
module tb_full_service_exact;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg host_rd_valid=0,host_rsp_ready=0,host_wr_valid=0,host_ack_ready=0;
 reg [8:0] host_a=0,host_b=0,host_dst=0;
 reg [4095:0] host_wdata=0;
 wire host_rd_ready,host_rsp_valid,host_wr_ready,host_ack_valid;
 wire [4095:0] host_rsp_a,host_rsp_b;
 reg simd_valid=0,simd_mul=0,simd_done_ready=0;
 reg [8:0] simd_a=0,simd_b=0,simd_dst=0;
 wire simd_ready,simd_done,simd_fault;
 reg scratch_valid=0,scratch_write=0,scratch_done_ready=0;
 reg [9:0] scratch_addr=0;reg [511:0] scratch_wdata=0;
 wire scratch_ready,scratch_done;wire [511:0] scratch_rdata;
 ot_gpu_full_sm_service #(.ENABLE(1)) dut(.*);
 integer k,n,cycles;
 reg [4095:0] av,bv,expected;
 reg fault_expected;
 task tick;begin @(posedge clk);#1;end endtask
 task put(input [8:0] dst,input [4095:0] value);
  begin @(negedge clk);host_wr_valid=1;host_dst=dst;host_wdata=value;
   #1;if(!host_wr_ready) $fatal(1,"host write blocked");tick;
   if(!host_ack_valid) $fatal(1,"write ACK missing");
   @(negedge clk);host_wr_valid=0;host_ack_ready=1;tick;
   @(negedge clk);host_ack_ready=0;
  end
 endtask
 task run_op(input reg multiply,input [8:0] destination);
  begin
   put(127,av);put(128,bv);
   @(negedge clk);simd_valid=1;simd_mul=multiply;simd_a=127;simd_b=128;simd_dst=destination;
   #1;if(!simd_ready) $fatal(1,"SIMD admission");tick;
   @(negedge clk);simd_valid=0;host_rd_valid=1;host_a=destination;host_b=destination;
   cycles=0;
   while(!simd_done && cycles<32) begin tick;cycles=cycles+1;
    if(host_rd_ready || host_rsp_valid) $fatal(1,"SIMD reservation lost");
   end
   if(!simd_done || cycles!=12) $fatal(1,"SIMD latency expected12 got %0d",cycles);
   if(simd_fault!==fault_expected) $fatal(1,"SIMD fault mismatch");
   repeat(4) begin tick;if(!simd_done || host_rd_ready || simd_fault!==fault_expected) $fatal(1,"done lease unstable");end
   @(negedge clk);simd_done_ready=1;tick;
   @(negedge clk);simd_done_ready=0;
   #1;if(!host_rd_ready) $fatal(1,"RF not released");tick;
   @(negedge clk);host_rd_valid=0;tick;
   if(!host_rsp_valid || host_rsp_a!==expected || host_rsp_b!==expected) $fatal(1,"full-lane arithmetic/result/mirror exact FAIL");
   @(negedge clk);host_rsp_ready=1;tick;
   @(negedge clk);host_rsp_ready=0;
  end
 endtask
 initial begin
  repeat(2) tick;@(negedge clk);rst_n=1;
  // Mixed lanes: signs, RNE even/odd ties, subnormal, zero and overflow refusal.
  for(k=0;k<128;k=k+1) case(k%8)
   0:begin av[k*32+:32]=32'h3f800000;bv[k*32+:32]=32'h40000000;expected[k*32+:32]=32'h40400000;end
   1:begin av[k*32+:32]=32'h3f800000;bv[k*32+:32]=32'h33800000;expected[k*32+:32]=32'h3f800000;end
   2:begin av[k*32+:32]=32'h3f800001;bv[k*32+:32]=32'h33800000;expected[k*32+:32]=32'h3f800002;end
   3:begin av[k*32+:32]=32'h00000001;bv[k*32+:32]=32'h00000001;expected[k*32+:32]=32'h00000002;end
   4:begin av[k*32+:32]=32'hc0000000;bv[k*32+:32]=32'h3f800000;expected[k*32+:32]=32'hbf800000;end
   5:begin av[k*32+:32]=32'h40000000;bv[k*32+:32]=32'hbf800000;expected[k*32+:32]=32'h3f800000;end
   6:begin av[k*32+:32]=32'h00000000;bv[k*32+:32]=32'h80000000;expected[k*32+:32]=32'h00000000;end
   7:begin av[k*32+:32]=32'h7f7fffff;bv[k*32+:32]=32'h7f7fffff;expected[k*32+:32]=32'h00000000;end
  endcase
  fault_expected=1;run_op(0,511);
  for(k=0;k<128;k=k+1) case(k%4)
   0:begin av[k*32+:32]=32'h3f800000;bv[k*32+:32]=32'h40000000;expected[k*32+:32]=32'h40000000;end
   1:begin av[k*32+:32]=32'hbf800000;bv[k*32+:32]=32'h40000000;expected[k*32+:32]=32'hc0000000;end
   2:begin av[k*32+:32]=32'h00000001;bv[k*32+:32]=32'h40000000;expected[k*32+:32]=32'h00000002;end
   3:begin av[k*32+:32]=32'h80000000;bv[k*32+:32]=32'h40000000;expected[k*32+:32]=32'h00000000;end
  endcase
  fault_expected=0;run_op(1,511);
  // Destination aliases an operand in a second invocation; mirrored ACK must
  // make both reads observe exactly the committed result on the next operation.
  run_op(1,127);
  $display("PASS full128 SIMD directed RNE/sign/subnormal/refusal;12cycle done;mirrors;leases");$finish;
 end

endmodule
