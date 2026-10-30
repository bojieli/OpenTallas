`timescale 1ps/1fs
module tb;
 parameter integer MUT=0;
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=0;
 reg [15:0]rq=0,rr=0;reg[383:0]ra=0;
 wire[511:0]rd0,rd1;reg[7:0]sr_v=0;reg[119:0]sr_addr=0;
 wire[2047:0]sr_d0,sr_d1;wire[7:0]sr_rv0,sr_rv1;
 reg[7:0]sw_v=0;reg[119:0]sw_addr=0;reg[63:0]sw_mask=0;reg[2047:0]sw_d=0;
 reg[0:0]lw=0;reg[23:0]lwa=0;reg[31:0]lwd=0;reg s1_v=0;reg[14:0]s1_a=0;reg[31:0]s1_d=0;
 wire flt0,flt1;
 ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.NS(8))r(
 .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rr),.ra(ra),.rd(rd0),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(sr_d0),.sr_rv(sr_rv0),
 .sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.lw(lw),.lwa(lwa),.lwd(lwd),.s1_v(s1_v),.s1_a(s1_a),.s1_d(s1_d),.flt(flt0));
 ot_hgi_su_lgroup2_bankchunks #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.NS(8),.MUT_CHUNK(MUT))c(
 .clk(clk),.rst_n(rst_n),.rq(rq),.rr(rr),.ra(ra),.rd(rd1),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(sr_d1),.sr_rv(sr_rv1),
 .sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.lw(lw),.lwa(lwa),.lwd(lwd),.s1_v(s1_v),.s1_a(s1_a),.s1_d(s1_d),.flt(flt1));
 integer steps=0,bad=0,known=0,seed=32'h2ac01913;
 task tick;begin
  @(posedge clk);#1;steps=steps+1;
  if(rd0!==rd1||sr_d0!==sr_d1||sr_rv0!==sr_rv1||flt0!==flt1)bad=bad+1;
  if(rq==16'hffff && (^rd0)!==1'bx)known=known+512;
 end endtask
 function integer bank(input integer lane,input integer k);
  if(k==0)bank=lane;
  else if(k==1)bank=lane^1;
  else bank=(lane>>1)+(k-2)*8;
 endfunction
 integer row,l,k,t,a;
 initial begin
  repeat(3)begin @(negedge clk);tick;end
  @(negedge clk);rst_n=1;tick;
  // Fill every one of 32768 words, 16 distinct banks per edge. No reduced memory vehicle.
  for(row=0;row<2048;row=row+1)begin
   @(negedge clk);sw_v=8'h03;sw_mask=64'hffff;sw_addr[0+:15]=15'(row*16);sw_addr[15+:15]=15'(row*16+8);
   for(l=0;l<16;l=l+1)sw_d[l*32+:32]=32'(row*16+l)^32'h719ac031;
   tick;
  end
  @(negedge clk);sw_v=0;sw_mask=0;tick;
  // Every candidate family, all four groups, and lane 0's unrestricted bank access.
  for(t=0;t<256;t=t+1)begin
   @(negedge clk);rq=16'hffff;rr=16'hffff;
   for(l=0;l<16;l=l+1)begin
    k=t%4;a=(l==0)?(t%16):bank(l,k);ra[l*24+:24]=24'(((t*7)%2048)*16+a);
   end
   tick;
  end
  // Actual NS=8 sector ports. All active sectors agree on bank rows, preserving legal multiple-read behavior.
  for(t=0;t<128;t=t+1)begin
   @(negedge clk);rq=0;rr=0;sr_v=8'hff;
   for(l=0;l<8;l=l+1)sr_addr[l*15+:15]=15'(((t*11)%2048)*16+(l%2)*8);
   tick;
  end
  // Check stream write priority and conflict status alongside initialized memory reads.
  for(t=0;t<128;t=t+1)begin
   @(negedge clk);sr_v=0;rq=16'hffff;rr=16'hffff;s1_v=1;s1_a=15'(t*17);s1_d=32'(t)^32'h11882244;
   sw_v=(t%3==0)?8'h01:8'h00;sw_addr[0+:15]=15'(t*17);sw_mask[0+:8]=8'hff;
   for(l=0;l<16;l=l+1)ra[l*24+:24]=24'((t%2048)*16+l);
   tick;
  end
  @(negedge clk);s1_v=0;sw_v=0;rq=0;rr=0;rst_n=0;tick;
  @(negedge clk);rst_n=1;tick;
  $display("BANKCHUNK_ACTUAL_M16 words=32768 NS=8 SRAM=16 steps=%0d known_bits=%0d bad=%0d mutant=%0d",steps,known,bad,MUT);
  if(MUT==0 && bad!=0)$fatal(1,"bankchunk lockstep mismatch");
  if(MUT!=0 && bad==0)$fatal(1,"write mutant escaped");
  if(known<131072)$fatal(1,"insufficient initialized read coverage");
  $finish;
 end
endmodule
