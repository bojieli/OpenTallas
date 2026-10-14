`timescale 1ns/1ps
module tb_hfd_tkm_native_credit;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 wire[3:0]grant;wire ack,rx_fault;
 wire[39:0]control={1'b0,1'b0,6'd62,23'd0,ack,grant,4'd0};
 reg wv=0,cdone=0,ready=0;reg[39:0]wa;reg[15:0]wm;reg[511:0]wd;
 wire wr,done,busy,fault;wire[15:0]pending;wire[4:0]leases;wire[544:0]packet;
 wire rv;wire[39:0]ra;wire[15:0]rm;wire[511:0]rd;
 integer sent=0,received=0,cycles=0,i;
 ot_hfd_tkm_write_credit_tx #(.MUT(MUT))tx(.clk(clk),.rst_n(rst_n),.control(control),.w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.w_rdy(wr),.packet(packet),.core_done(cdone),.core_busy(1'b0),.core_fault(1'b0),.done(done),.busy(busy),.fault(fault),.outstanding(pending),.leases(leases));
 ot_hfd_tkm_write_credit_rx rx(.clk(clk),.rst_n(rst_n),.packet(packet),.w_v(rv),.w_addr(ra),.w_mask(rm),.w_data(rd),.w_rdy(ready),.grant(grant),.ack(ack),.fault(rx_fault));
 always @(negedge clk)begin
  // Fill all eight leases under a long initial stall; later stall bursts.
  ready=(cycles>120)&&(cycles%11<5);
  wv=rst_n&&sent<64;wa=40'hc51234fff0+sent*16;wm=16'(sent*17+3);
  for(integer i=0;i<16;i=i+1)wd[32*i+:32]=32'hb1770000+sent*16+i;
  cdone=sent==64;
 end
 always @(posedge clk)begin
  cycles=cycles+1;
  if(wv&&wr)sent=sent+1;
  if(rv&&ready)begin
   if(ra!==40'hc51234fff0+received*16||rm!==16'(received*17+3))$fatal(1,"NATIVE_CREDIT FAIL address/mask");
   for(integer i=0;i<16;i=i+1)if(rd[32*i+:32]!==32'hb1770000+received*16+i)$fatal(1,"NATIVE_CREDIT FAIL data");
   received=received+1;
  end
  if(fault||rx_fault)$fatal(1,"NATIVE_CREDIT FAIL credit/parser fault");
  if(done)begin
   if(received!=64||pending!=0)$fatal(1,"NATIVE_CREDIT FAIL early done received=%0d pending=%0d",received,pending);
   $display("NATIVE_CREDIT PASS writes=%0d fullpayloadwords=%0d cycles=%0d",received,received*16,cycles);$finish;
  end
  if(cycles>3000)$fatal(1,"NATIVE_CREDIT FAIL timeout");
 end
 initial begin repeat(8)@(negedge clk);rst_n=1;end
endmodule
