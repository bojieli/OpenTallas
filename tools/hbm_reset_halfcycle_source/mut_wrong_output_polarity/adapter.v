// FOUR-STATE FUNCTIONAL ADAPTER ONLY, directly from hashed native Liberty equations.
// Not a Liberty replacement, timing model, min-pulse check or physical primitive.
module TIEHIx1_ASAP7_75t_R(output H); assign H=1'b1; endmodule
module BUFx12f_ASAP7_75t_R(input A,output Y); assign Y=A; endmodule
module INVx1_ASAP7_75t_R(input A,output Y); assign Y=~A; endmodule
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output QN);
 reg IQN;
 always @(posedge CLK or negedge RESETN or negedge SETN)
  if(!RESETN && SETN) IQN<=1'b1;
  else if(RESETN && !SETN) IQN<=1'b0;
  else if(!RESETN && !SETN) IQN<=1'b0; // clear_preset_var1 : L
  else IQN<=!D;
 assign QN=(!RESETN && SETN) ? 1'b1 : (RESETN && !SETN) ? 1'b0 : (!RESETN && !SETN) ? 1'b0 : IQN;
endmodule

module INVx6_ASAP7_75t_R(input A,output Y); assign Y=A; endmodule
