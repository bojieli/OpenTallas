`ifndef SYNTHESIS
`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;integer n=0,high_age=0,low_age=0,errors=0;
 wire[6:0]q;
 genvar g;
 generate for(g=0;g<7;g=g+1)begin:uut
  localparam integer L=g==0?2:g==1?3:g==2?4:g==3?18:g==4?36:g==5?60:78;
  qfd_c_reset_epoch #(.RELEASE(L),.MUT(MUT))u(ck,rst,q[g]);
  always@(posedge ck)begin
   #0.1;
   if((rst&&q[g]!== (high_age>=L))||(!rst&&low_age>=3&&q[g]!==1'b0))begin
    errors=errors+1;if(errors<5)$display("RST_EPOCH_MISMATCH L%0d MUT%0d cycle%0d highage%0d",L,MUT,n,high_age);
   end
  end
 end endgenerate
 always@(negedge ck)begin n=n+1;rst=(n>=100&&n<300)||(n>=400&&n<650)||(n>=750);end
 always@(posedge ck)begin
  if(rst)begin high_age=high_age+1;low_age=0;end
  else begin high_age=0;low_age=low_age+1;end
  #1;
  if(n>=1000)begin
   if(errors)$fatal(1,"RST_EPOCH_FAIL MUT%0d errors%0d",MUT,errors);
   $display("RST_EPOCH_PASS MUT%0d",MUT);$finish;
  end
 end
endmodule
`endif
