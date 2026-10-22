// Opt-in post-relay fault observation leaf. No GEN default adoption.
// Actual group rs is the reset epoch; capture starts at its first real ck edge.
// N sticky input flops + 2 release flops + reduction/output flops = N+4.
// rs direct mapped endpoint census owed (raw structural N+2 <=18); rl[1] ->2.
// Domains are never combined here. Physical pins/reach/clock/CDC remain unqualified.
module qfd_fault_capture #(parameter int N=16) (
 input wire ck, rs, input wire [N-1:0] f, output reg o
);
 initial if (N<1 || N>16) $error("qfd_fault_capture N outside1..16");
 reg [1:0] rl;
 always @(posedge ck or negedge rs)
   if (!rs) rl<=2'b00; else rl<={rl[0],1'b1};
 reg [N-1:0] fq;
 always @(posedge ck or negedge rs)
   if (!rs) fq<={N{1'b0}};
`ifdef QFD_CAPTURE_MUT_DELAY
   else if (!rl[1]) fq<={N{1'b0}};
`endif
`ifdef QFD_CAPTURE_MUT_NONSTICKY
   else fq<=f;
`else
   else fq<=fq|f;
`endif
 reg s;
 always @(posedge ck or negedge rl[1])
   if (!rl[1]) begin s<=1'b0; o<=1'b0; end
   else begin s<=|fq; o<=s; end
endmodule
