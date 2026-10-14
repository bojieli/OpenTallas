`timescale 1ns/1ps
module tb_hfd_tkm_native_output_leaf;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rx_reset=0,start=0,cv=0,last=0,ready=0,cdone=0;
 reg[339:0]ct;reg[1:0]slot;wire[544:0]packet;
 wire[3:0]grant,queued;wire ack,rf,done,busy,fault,pe;wire[9:0]lp;
 wire[39:0]control={2'b0,6'd62,23'd0,ack,grant,4'b0};
 wire rv;wire[39:0]ra;wire[15:0]rm;wire[511:0]rd;
 integer received=0,cycles=0,c,i,ix,line,idx;reg[31:0]expected;
 ot_hfd_tkm_native_output_leaf #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.start(start),
 .cfg_nout(13'd128),.cfg_obase(40'hf88123fff0),.cfg_rbase(40'h208765fff0),.cfg_has_r(1'b1),
 .cell_v(cv),.cell_t(ct),.cell_slot(slot),.cell_last(last),.native_control(control),
 .core_done(cdone),.core_busy(!cdone),.core_fault(1'b0),.native_write(packet),.done(done),.busy(busy),.fault(fault),.queued(queued),.lines_pushed(lp),.pack_empty(pe));
 ot_hfd_tkm_write_credit_rx rx(.clk(clk),.rst_n(rx_reset),.packet(packet),.w_v(rv),.w_addr(ra),.w_mask(rm),.w_data(rd),.w_rdy(ready),.grant(grant),.ack(ack),.fault(rf));
 always @(negedge clk)ready=(cycles>120)&&(cycles%11<6);
 always @(posedge clk)begin
  cycles=cycles+1;
  if(rv&&ready)begin
   line=received/2;
   if(ra!==((received%2)?40'h208765fff0:40'hf88123fff0)+16*line||rm!==16'hffff)$fatal(1,"NATIVE_OUTPUT FAIL address/mask");
   for(integer i=0;i<16;i=i+1)begin
    idx=16*line+i;expected=(received%2)?((idx%7==0)?32'h80000000:32'h3f800000):(32'h12340000+idx);
    if(rd[32*i+:32]!==expected)$fatal(1,"NATIVE_OUTPUT FAIL payload line=%0d i=%0d",received,i);
   end
   received=received+1;
  end
  if(fault||rf)$fatal(1,"NATIVE_OUTPUT FAIL fault");
  if(done)begin
   if(received!=16)$fatal(1,"NATIVE_OUTPUT FAIL early completion");
   $display("NATIVE_OUTPUT PASS O_R_writes=16 checked=256 cycles=%0d",cycles);$finish;
  end
  if(cycles>3000)$fatal(1,"NATIVE_OUTPUT FAIL timeout received=%0d",received);
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(16)@(negedge clk);rx_reset=1;
  repeat(8)@(negedge clk);start=1;@(negedge clk);start=0;repeat(4)@(negedge clk);
  for(c=0;c<32;c=c+1)begin
   while(queued>4)@(negedge clk);
   for(ix=0;ix<4;ix=ix+1)begin idx=4*c+ix;ct[85*ix+:85]={1'b1,1'b0,~(32'h12340000+idx),32'hbf800000,18'd0,(idx%7==0)};end
   cv=1;slot=c%4;last=c==31;@(negedge clk);
  end
  cv=0;last=0;repeat(3)@(negedge clk);
  while(!pe)@(negedge clk);cdone=1;@(negedge clk);cdone=0;
 end
endmodule
