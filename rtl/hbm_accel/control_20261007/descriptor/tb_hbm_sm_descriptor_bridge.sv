module tb_hbm_sm_descriptor_bridge;
 parameter HOPS=12;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,s_valid=0,d_ready=0,south_fault=0;
 reg[31:0]s_base=0;reg[23:0]s_lines=0;
 wire s_ready,d_valid,north_fault,fault;wire[31:0]d_base;wire[23:0]d_lines;
 ot_hbm_sm_descriptor_bridge #(.ENABLE(1),.HOPS(HOPS)) dut(.*);
 integer sent=0,consumed=0,acknowledged=0,cyc=0,i;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(cyc>64*(2*HOPS+40))$fatal(1,"descriptor bounded progress");
  if(d_valid && d_ready)begin
   if(d_base!==32'h80000000+consumed*128 || d_lines!==consumed+1)$fatal(1,"descriptor order/data");
   consumed=consumed+1;
  end
  if(s_valid && s_ready)begin
   if(consumed<=acknowledged)$fatal(1,"credit was misrepresented as actual consumption");
   acknowledged=acknowledged+1;
  end
  if(fault)$fatal(1,"bridge fault");
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(i=0;i<64;i=i+1)begin
   s_valid=1;s_base=32'h80000000+i*128;s_lines=i+1;d_ready=0;
   // Receiver stalls longer than flight; no parent ACK is allowed yet.
   repeat(HOPS+7)begin @(negedge clk);if(s_ready)$fatal(1,"premature parent acknowledgement");end
   d_ready=1;#1;
   while(!s_ready)@(negedge clk);
   @(negedge clk);s_valid=0;d_ready=0;
   repeat(2)@(negedge clk);
  end
  if(consumed!=64 || acknowledged!=64)$fatal(1,"descriptor counts");
  south_fault=1;repeat(HOPS+2)@(negedge clk);
  if(!north_fault)$fatal(1,"south fault lost");
  $display("PASS descriptors=64 consumed=64 acknowledged=64 hops=%0d cycles=%0d",HOPS,cyc);$finish;
 end
endmodule
