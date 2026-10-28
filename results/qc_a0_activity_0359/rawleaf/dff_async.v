module DFFASRHQNx1_ASAP7_75t_R(output reg QN,input D,RESETN,SETN,CLK);
always @(posedge CLK or negedge RESETN or negedge SETN) if(!RESETN && !SETN) QN<=1'b0; else if(!RESETN) QN<=1'b1; else if(!SETN) QN<=1'b0; else QN<=~D;
endmodule
