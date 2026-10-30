module BUFx2_ASAP7_75t_R(input A,output Y); buf(Y,A); endmodule
module HB4xp67_ASAP7_75t_R(input A,output Y); buf(Y,A); endmodule
module tb;
 reg a; wire b0,b1,old_y,new_y,mut_y;
 BUFx2_ASAP7_75t_R o0(a,b0),o1(b0,b1),o2(b1,old_y);
 HB4xp67_ASAP7_75t_R n0(a,new_y),m0(~a,mut_y);
 integer k,caught=0;
 initial begin
  for(k=0;k<4;k=k+1) begin
   case(k) 0:a=0; 1:a=1; 2:a=1'bx; 3:a=1'bz; endcase
   #1;
   if(old_y!==new_y) $fatal(1,"positive buffer contraction mismatch on vector %0d",k);
   if(old_y!==mut_y) caught=caught+1;
  end
  if(caught!=2) $fatal(1,"mutant did not distinguish both defined states");
  $display("BUFFER_CONTRACTION_PASS vectors=4 mutant_caught=2 cycles_added=0");
 end
endmodule
