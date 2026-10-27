module DFFHQNx2_ASAP7_75t_R(output reg QN,input D,CLK); always @(posedge CLK) QN<=~D; endmodule
