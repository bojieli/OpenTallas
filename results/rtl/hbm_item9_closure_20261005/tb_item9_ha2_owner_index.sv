`timescale 1ps/1ps
module tb_item9_ha2_owner_index;
 reg[7:0]rank;reg[15:0]pf,f;wire match;wire[15:0]slot;
 ot_ha2_item9_own_index dut(.rank(rank),.pf(pf),.f(f),.match(match),.slot(slot));
 integer tests=0;
 initial begin
  for(integer ofl=2;ofl<=48;ofl=ofl+2)begin
   pf=ofl*8;
   for(integer j=0;j<8;j=j+1)begin
    rank=j;
    for(integer k=0;k<65536;k=k+1)begin
     f=k;#1;
     if(match !== (k/ofl==j))$fatal(1,"owner match pf%0d j%0d f%0d",pf,j,k);
     if(match && slot !== 16'(k%ofl))$fatal(1,"slot pf%0d j%0d f%0d",pf,j,k);
     tests=tests+1;
    end
   end
  end
  for(integer j=0;j<256;j=j+1)begin
   rank=j;pf=384;f=(j%8)*48+47;#1;
   if(!match||slot!==16'd47)$fatal(1,"full rank namespace");tests=tests+1;
  end
  $display("PASS actualHA2 owner-index exhaustive tests=%0d zero newcycles",tests);$finish;
 end
endmodule
