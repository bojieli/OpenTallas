`timescale 1ns/1ps
module tb_storage;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rd_valid=0,wr_valid=0,rsp_ready=0,ack_ready=0;
 reg [8:0] rd_a=0,rd_b=0,wr_addr=0;
 reg [4095:0] wr_data=0;
 wire rd_ready,wr_ready,rsp_valid,ack_valid;
 wire [4095:0] rsp_a,rsp_b;
 ot_gpu_rf_service rf(.*);
 reg valid=0,write=0,done_ready=0;
 reg [9:0] addr=0;reg [511:0] wdata=0;
 wire ready,done;wire [511:0] rdata;
 ot_gpu_scratch_service scratch(.*);
 integer n,l;
 function automatic [4095:0] vector(input integer a);
  integer k;begin for(k=0;k<128;k=k+1) vector[k*32+:32]=32'h81ab0000 ^ (a<<7) ^ k;end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task put(input integer a);
  begin @(negedge clk);wr_addr=a;wr_data=vector(a);wr_valid=1;
   if(!wr_ready) $fatal(1,"unexpected write stall");tick;
   if(!ack_valid) $fatal(1,"missing mirrored ACK");
   @(negedge clk);wr_valid=0;ack_ready=1;tick;
   @(negedge clk);ack_ready=0;
  end
 endtask
 task get(input integer a,input integer b);
  begin @(negedge clk);rd_a=a;rd_b=b;rd_valid=1;
   if(!rd_ready) $fatal(1,"unexpected read stall");tick;
   if(rsp_valid) $fatal(1,"early response");
   @(negedge clk);rd_valid=0;tick;
   if(!rsp_valid || rsp_a!==vector(a) || rsp_b!==vector(b)) $fatal(1,"RF full-lane mismatch %d %d",a,b);
   @(negedge clk);rsp_ready=1;tick;
   @(negedge clk);rsp_ready=0;
  end
 endtask
 initial begin
  repeat(2) tick;@(negedge clk);rst_n=1;
  for(n=0;n<512;n=n+1) put(n);
  for(n=0;n<512;n=n+1) get(n,511-n);
  // Hold a live read lease; competing write remains unaccepted and data stable.
  @(negedge clk);rd_a=127;rd_b=384;rd_valid=1;tick;
  @(negedge clk);rd_valid=0;tick;
  @(negedge clk);wr_valid=1;wr_addr=127;wr_data=vector(0);
  repeat(6) begin tick;if(wr_ready || !rsp_valid || rsp_a!==vector(127) || rsp_b!==vector(384)) $fatal(1,"lease violation");end
  @(negedge clk);rsp_ready=1;tick;
  @(negedge clk);rsp_ready=0;tick;
  if(!ack_valid) $fatal(1,"write not resumed");
  @(negedge clk);wr_valid=0;ack_ready=1;tick;
  @(negedge clk);ack_ready=0;
  // Held mirrored-write ACK fences subsequent readers until retirement.
  @(negedge clk);wr_valid=1;wr_addr=17;wr_data=vector(17);tick;
  @(negedge clk);wr_valid=0;rd_valid=1;rd_a=17;rd_b=17;
  repeat(6) begin tick;if(!ack_valid || rd_ready || rsp_valid) $fatal(1,"ACK fence violation");end
  @(negedge clk);ack_ready=1;tick;
  @(negedge clk);ack_ready=0;tick;
  @(negedge clk);rd_valid=0;tick;
  if(!rsp_valid || rsp_a!==vector(17) || rsp_b!==vector(17)) $fatal(1,"ACK visible mirror mismatch");
  @(negedge clk);rsp_ready=1;tick;
  @(negedge clk);rsp_ready=0;
  // Re-establish last-write arbitration state for the conflict test.
  put(17);
  // Simultaneous bank-conflicting requests: only one grant; alternate next turn.
  @(negedge clk);rd_valid=1;wr_valid=1;rd_a=0;rd_b=0;wr_addr=1;wr_data=vector(1);
  #1;if(rd_ready==wr_ready) $fatal(1,"conflicting grant");
  // Last transaction was a write, hence read first.
  if(!rd_ready) $fatal(1,"fair read turn");tick;
  @(negedge clk);rd_valid=0;tick;
  @(negedge clk);rsp_ready=1;tick;
  @(negedge clk);rsp_ready=0;tick;
  if(!ack_valid) $fatal(1,"fair write turn");
  @(negedge clk);wr_valid=0;ack_ready=1;tick;
  @(negedge clk);ack_ready=0;
  for(n=0;n<1024;n=n+1) begin
   @(negedge clk);valid=1;write=1;addr=n;for(l=0;l<16;l=l+1) wdata[l*32+:32]=n*16+l;
   if(!ready) $fatal(1,"scratch write stall");tick;
   if(!done) $fatal(1,"scratch ACK");
   @(negedge clk);valid=0;done_ready=1;tick;
   @(negedge clk);done_ready=0;
  end
  for(n=0;n<1024;n=n+1) begin
   @(negedge clk);valid=1;write=0;addr=n;tick;
   @(negedge clk);valid=0;tick;
   if(!done) $fatal(1,"scratch read missing");
   for(l=0;l<16;l=l+1) if(rdata[l*32+:32]!==n*16+l) $fatal(1,"scratch mismatch");
   repeat(3) begin tick;if(ready || !done) $fatal(1,"scratch backpressure");end
   @(negedge clk);done_ready=1;tick;
   @(negedge clk);done_ready=0;
  end
  // Reset cancels lease/ACK state; storage contents have no reset guarantee.
  @(negedge clk);rd_valid=1;tick;
  @(negedge clk);rst_n=0;rd_valid=0;tick;
  if(rsp_valid || ack_valid || done || rd_ready || wr_ready || ready) $fatal(1,"reset retirement");
  $display("PASS storage: 512 RF vectors x128 lanes x2 copies;1024 scratch beats;leases/conflicts/reset");$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
