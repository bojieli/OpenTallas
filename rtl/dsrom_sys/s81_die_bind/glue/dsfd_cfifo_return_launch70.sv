`timescale 1ns/1ps
// Optional north capture -> south launch split, one explicitly priced return edge.
// Not selected by dsfd_cfifo_partitioned. Compiler/die integration is still required.
module dsfd_cfifo_return_launch70(input wire ck,input wire [69:0] d,output wire [69:0] q);
`ifdef OT_CFIFO_RETURN_MUT_BYPASS
 assign q=d;
`else
 reg [69:0] q_r;
 always @(posedge ck)q_r<=d;
 assign q=q_r;
`endif
endmodule
