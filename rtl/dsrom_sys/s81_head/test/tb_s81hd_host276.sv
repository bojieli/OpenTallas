`timescale 1ns/1ps
module tb_s81hd_host276;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,v=0;reg[552:0]frame=0;
 wire[275:0]lane,mlane;wire rv,mrv,tf,rf,mtf,mrf;wire[552:0]out,mout;
 ot_s81hd_host276_tx tx(.*,.fault(tf));
 ot_s81hd_host276_rx rx(.ck(ck),.rn(rn),.lane(lane),.v(rv),.frame(out),.fault(rf));
 ot_s81hd_host276_tx #(.MUT_HIGH(1))mtx(.ck(ck),.rn(rn),.v(v),.frame(frame),.lane(mlane),.fault(mtf));
 ot_s81hd_host276_rx mrx(.ck(ck),.rn(rn),.lane(mlane),.v(mrv),.frame(mout),.fault(mrf));
 reg[552:0]expected[0:2047];integer sent=0,received=0,mutants=0,cyc=0;
 integer first_in=-1,first_out=-1;integer k,j;
 always @(posedge ck)begin
  cyc=cyc+1;
  if(rn&&v)begin expected[sent]=frame;sent=sent+1;if(first_in<0)first_in=cyc;end
  #1;
  if(rn&&rv)begin
   if(out!==expected[received])$fatal(1,"HOST276 lockstep mismatch %0d",received);
   if(!mrv||mout===expected[received])$fatal(1,"high-bit mutant escaped");
   mutants=mutants+1;received=received+1;if(first_out<0)first_out=cyc;
  end
 end
 initial begin
  repeat(4)@(negedge ck);rn=1;
  for(k=0;k<1024;k=k+1)begin
   @(negedge ck);for(j=0;j<18;j=j+1)begin frame=(frame<<32)|553'($urandom);end
   if(k<553)frame=553'd1<<k;v=1;
   @(negedge ck);v=0;
   repeat(1)@(negedge ck);
   if(k%17==0)repeat(3)@(negedge ck);
  end
  repeat(6)@(negedge ck);
  if(received!=1024||mutants!=1024||tf||rf||mtf||mrf)$fatal(1,"counts or faults");
  $display("HOST276 PASS records=%0d mutant_caught=%0d sampled_edge_delta=%0d",received,mutants,first_out-first_in);$finish;
 end
endmodule
