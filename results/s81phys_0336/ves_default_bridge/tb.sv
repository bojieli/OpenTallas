`timescale 1ps/1fs
module tb;
reg clk=0; always #416.5 clk=~clk;
reg[255:0]d=0,d2=0;wire[255:0]gq,gq2,nq,nq2,bq,bq2;
genvar t;generate for(t=0;t<8;t=t+1)begin:g
 gold_dly #(.W(32),.D(4*t),.MUT(0)) a(clk,d[32*t+:32],d2[32*t+:32],gq[32*t+:32],gq2[32*t+:32]);
 new_dly #(.W(32),.D(4*t),.MUT(0)) n(clk,d[32*t+:32],d2[32*t+:32],nq[32*t+:32],nq2[32*t+:32]);
 bad_dly #(.W(32),.D(4*t),.MUT(0)) m(clk,d[32*t+:32],d2[32*t+:32],bq[32*t+:32],bq2[32*t+:32]);
 // One legal common initial pointer state for the witness only; the primary AIG proof covers ALL common states.
 if(t>0)begin:seed initial begin a.g_ring.u.wptr=0;n.g_ring.u.wptr=0;m.g_ring.u.wptr=0;end end
end endgenerate
integer i,j,checks=0,mut=0,first=-1;reg[31:0]r=32'h93e17ab1;
initial begin
 for(i=0;i<2000;i=i+1)begin
  @(negedge clk);
  for(j=0;j<8;j=j+1)begin r=r^(r<<13);r=r^(r>>17);r=r^(r<<5);d[32*j+:32]=r;d2[32*j+:32]=~r;end
  @(posedge clk);#1;
  if(i>=64)begin
   if((^gq)===1'bx || (^gq2)===1'bx)$fatal(1,"X output afterwarmup cycle%0d",i);
   if({gq,gq2}!=={nq,nq2})$fatal(1,"DEFAULT_OFF_MITER_FAIL cycle%0d",i);
   checks=checks+16;
   if({gq,gq2}!=={bq,bq2})begin mut=mut+1;if(first<0)first=i;end
  end
 end
 if(mut==0)$fatal(1,"wrongZERO_LOW1controlnotdetected");
 $display("DEFAULT_OFF_MITER_PASS cycles=2000 checks=%0d added_cycles=0 MUTANT_CAUGHT_cycles=%0d first=%0d",checks,mut,first);$finish;
end
endmodule
