`timescale 1ns/1ps
module old_counter(input ck,rst_n,pop,ret,output reg[3:0]c);
 always @(posedge ck,negedge rst_n)if(!rst_n)c<=4'h5;else c<=(c-{3'b0,pop})+{3'b0,ret};
endmodule
module encoded_counter(input ck,rst_n,pop,ret,output wire[3:0]c);
 reg[3:0]base;reg q;
 assign c=base+{3'b0,q};
 always @(posedge ck,negedge rst_n)if(!rst_n)begin base<=4'h5;q<=0;end else begin base<=c-{3'b0,pop};q<=ret;end
endmodule
module tb;
 reg ck=0;always #0.5 ck=~ck;reg rst_n=1,pop=0,ret=0;wire[3:0]oldc,newc;integer s,p,r,i,checks=0;reg[63:0]cov=0;reg[31:0]rng=32'h30c065a1;
 old_counter g(ck,rst_n,pop,ret,oldc);encoded_counter d(ck,rst_n,pop,ret,newc);
 task tick;begin
  @(negedge ck);if(rst_n&&(^oldc!==1'bx)&&(^pop!==1'bx)&&(^ret!==1'bx))cov[oldc*4+pop*2+ret]=1;
  @(posedge ck);#0.001;if(oldc!==newc)$fatal(1,"counter mismatch old%h new%h",oldc,newc);checks=checks+1;
 end endtask
 task reset;begin rst_n=0;#0.1;if(oldc!==4'h5||newc!==4'h5)$fatal(1,"async reset5 failed");tick;rst_n=1;pop=0;ret=0;end endtask
 initial begin
  #0.01;
  for(s=0;s<16;s=s+1)for(p=0;p<2;p=p+1)for(r=0;r<2;r=r+1)begin
   reset;
   for(i=0;i<((s-5+16)%16);i=i+1)begin pop=0;ret=1;tick;end
   if(oldc!==s[3:0])$fatal(1,"seedstate failed");pop=p;ret=r;tick;
  end
  reset;ret=1'bx;tick;ret=0;tick;
  reset;ret=1'bz;tick;ret=0;tick;
  reset;pop=1'bx;tick;pop=0;tick;
  reset;
  if(cov!==64'hffffffffffffffff)$fatal(1,"missing transitions %h",cov);
  $display("COUNTER_ENCODING PASS checks%0d all64binarytransitions all16states reset5 XZpropagation addedcycles0",checks);$finish;
 end
endmodule
