`timescale 1ns/1ps
module tb_dma_native_read;
 parameter integer MUT=0;
 reg clk=0;always #1 clk=~clk;reg rst_n=0;
 reg [512:0] oldq=0;wire [8256:0] oldr;wire [543:0] rq;
 reg [31:0] cr=0;reg [8223:0] rr=0;wire [39:0] fault;
 ot_hgi_dma_native_read_fabric #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.leaf_clk(40'd0),
 .legacy_q(oldq),.legacy_r(oldr),.native_rq(rq),.native_cr(cr),.native_rr(rr),.fault(fault));
 integer expected[32][$];integer native_sec[32][$];integer due[32][$];
 integer cycle=0,sent=0,checked=0,errors=0;integer issued[32];integer credit_count[32];
 function automatic [255:0] value(input integer sector);
  for(integer w=0;w<8;w=w+1)value[w*32 +:32]=32'(sector*8+w)^32'h9b147ead;
 endfunction
 always @(posedge clk)begin
  cycle=cycle+1;cr<=0;rr<=0;
  if(rst_n)begin
   for(integer l=0;l<32;l=l+1)begin
    if(oldq[l*16+15])begin expected[l].push_back(int'(oldq[l*16 +:15]));sent=sent+1;end
    if(oldr[l*257+256])begin
     integer sec;
     if(expected[l].size()==0)begin errors=errors+1;$display("DMA_NATIVE ERR unsolicited lane%0d",l);end
     else begin sec=expected[l].pop_front();if(oldr[l*257 +:256]!=value(sec))begin errors=errors+1;$display("DMA_NATIVE ERR payload/order lane%0d sector%0d",l,sec);end checked=checked+1;end
    end
    if(oldr[8224+l])credit_count[l]=credit_count[l]+1;
    if(rq[l*17+16])begin
     integer sec,t;
     sec=int'(rq[l*17 +:16]);t=cycle+5+(l/8)*5+$urandom_range(0,8);
     if(native_sec[l].size()!=0 && t<due[l][$])t=due[l][$];
     if(sec>=32768 || ((sec>>13)&3)!=l/8 || (sec&7)!=l%8)begin errors=errors+1;$display("DMA_NATIVE ERR native address lane%0d sector%0d",l,sec);end
     native_sec[l].push_back(sec);due[l].push_back(t);cr[l]<=1;
    end
    if(native_sec[l].size()!=0 && due[l][0]<=cycle)begin
     integer sec,t;sec=native_sec[l].pop_front();t=due[l].pop_front();rr[l*257 +:257]<={1'b1,value(sec)};
    end
   end
   if(|fault)begin errors=errors+1;$display("DMA_NATIVE ERR fault %h",fault);end
  end
 end
 always @(negedge clk)begin
  oldq=0;oldq[512]=rst_n;
  if(rst_n && cycle<2000)for(integer l=0;l<32;l=l+1)
   if(expected[l].size()<2 && $urandom_range(0,2)!=0)begin
    oldq[l*16 +:16]={1'b1,15'(($urandom_range(0,1023)<<5)|l)};issued[l]=issued[l]+1;
   end
 end
 initial begin
  for(integer l=0;l<32;l=l+1)begin issued[l]=0;credit_count[l]=0;end
  repeat(5)@(negedge clk);rst_n=1;
  wait(cycle>=2300);@(negedge clk);
  for(integer l=0;l<32;l=l+1)if(expected[l].size()!=0||native_sec[l].size()!=0||credit_count[l]!=issued[l])errors=errors+1;
  if(errors==0 && checked==sent && checked>1000)$display("DMA_NATIVE PASS checked=%0d sent=%0d cycles=%0d",checked,sent,cycle);
  else $display("DMA_NATIVE FAIL errors=%0d checked=%0d sent=%0d",errors,checked,sent);
  $finish;
 end
endmodule
