// 2-state functional form of ASAP7 supplied SEQ_RVT_TT altos_dff_sr_0.
// The published cell inverts D; SETN is active-low clear of QN,
// RESETN is active-low preset of QN; clear wins when both assert.
module DFFASRHQNx1_ASAP7_75t_R(output reg QN,input D,RESETN,SETN,CLK);
 always @(posedge CLK or negedge RESETN or negedge SETN)
  if(!SETN)QN<=1'b0;
  else if(!RESETN)QN<=1'b1;
  else QN<=~D;
endmodule
