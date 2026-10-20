module common_reset(input clk,rst_n,d,output wire equal,output reg q0,q1,output wire qualified_equal);
 always @(posedge clk or negedge rst_n)if(!rst_n)q0<=0;else q0<=d;
`ifdef WRONG_VALUE
 always @(posedge clk or negedge rst_n)if(!rst_n)q1<=1;else q1<=d;
`elsif MISSING_RESET
 always @(posedge clk)q1<=d;
`else
 always @(posedge clk or negedge rst_n)if(!rst_n)q1<=0;else q1<=
`ifdef WRONG_D
 ~d;
`else
 d;
`endif
`endif
 // Verification monitor only: source Q0/Q1 remain independent arbitrary initial state.
 reg reset_seen=0;
 always @(posedge clk or negedge rst_n)if(!rst_n)reset_seen<=1;else reset_seen<=reset_seen;
 assign equal=(q0==q1);
 assign qualified_equal=!reset_seen||equal;
endmodule
