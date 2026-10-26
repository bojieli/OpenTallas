`timescale 1ns/1ps
module tb_s81hd_best64;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,v=0;reg[552:0] frame=0;
 wire[63:0] lane,mlane;wire rv,mrv,tf,rf,mtf,mrf;
 wire[552:0] out,mout;
 ot_s81hd_best64_tx tx(.*,.fault(tf));
 ot_s81hd_best64_rx rx(.ck(ck),.rn(rn),.lane(lane),.v(rv),.frame(out),.fault(rf));
 ot_s81hd_best64_tx #(.MUT_IDENTITY(1)) mtx(.ck(ck),.rn(rn),.v(v),.frame(frame),.lane(mlane),.fault(mtf));
 ot_s81hd_best64_rx mrx(.ck(ck),.rn(rn),.lane(mlane),.v(mrv),.frame(mout),.fault(mrf));
 reg[552:0] expected[0:4095];integer sent=0,received=0,mutants=0,cyc=0;
 integer first_in=-1,first_out=-1;integer k,j;reg[96:0] bits;
 always @(posedge ck)begin
  cyc=cyc+1;
  if(rn&&v&&frame[552]&&frame[3:0]==1&&!(|frame[551:97]))begin
   expected[sent]=frame;sent=sent+1;
   if(first_in<0)first_in=cyc;
  end
  #1;
  if(rn&&rv)begin
   if(out!==expected[received])$fatal(1,"BEST64 lockstep mismatch %0d",received);
   if(!mrv||mout===expected[received])$fatal(1,"identity mutant escaped %0d",received);
   mutants=mutants+1;received=received+1;
   if(first_out<0)first_out=cyc;
  end
 end
 initial begin
  repeat(4)@(negedge ck);rn=1;
  // Every bit of the original 97-bit header+record, including both high
  // position bits and all user bits, is exercised. Contiguous two-edge
  // injections check sustained budget; later gaps check phase restart.
  for(k=0;k<1024;k=k+1)begin
   @(negedge ck);bits={$urandom,$urandom,$urandom,$urandom};bits[3:0]=1;
   if(k<97)bits=(97'd1<<k)|97'd1;
   bits[3:0]=1;frame={1'b1,455'd0,bits};v=1;
   @(negedge ck);v=0;
   if(k%17==0)repeat(3)@(negedge ck);
  end
  repeat(5)@(negedge ck);
  if(received!=1024||mutants!=1024||tf||rf||mtf||mrf)$fatal(1,"count/faults %0d/%0d tf%0b rf%0b",received,mutants,tf,rf);
  $display("BEST64 PASS records=%0d mutant_caught=%0d sampled_edge_delta=%0d",received,mutants,first_out-first_in);
  // Canonical-format violations must be explicit and must emit no word.
  @(negedge ck);frame=expected[0];frame[551]=1;v=1;
  @(negedge ck);v=0;repeat(4)@(negedge ck);
  if(!tf||received!=1024)$fatal(1,"reserved-bit violation accepted");
  $display("BEST64 format_guard PASS");$finish;
 end
endmodule
