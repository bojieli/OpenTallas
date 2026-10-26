`timescale 1ns/1ps
// Static face selection: exactly one input is connected to payload; other three
// require explicit per-instance constant zero proof. All output branches are real.
module ot_s81_rly4(input wire ck,rs,iN,iS,iE,iW, output wire oN,oS,oE,oW);
 wire d;
`ifdef OT_RLY4_INPUT_MUT
 assign d = iS | iE | iW;
`else
 assign d = iN | iS | iE | iW;
`endif
 reg q;
`ifdef OT_RLY4_EDGE_MUT
 always @(negedge ck or negedge rs)
`else
 always @(posedge ck or negedge rs)
`endif
`ifdef OT_RLY4_RESET_MUT
 if (!rs) q <= 1'b1;
`else
 if (!rs) q <= 1'b0;
`endif
 else q <= d;
 assign oN=q, oS=q, oE=q;
`ifdef OT_RLY4_OUTPUT_MUT
 assign oW=~q;
`else
 assign oW=q;
`endif
endmodule
