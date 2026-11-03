// For source-relation/mutant coupon only. NEVER read alongside native Liberty
// in mapped SYNTH. No reset/init. Fourteen physical QN states correspond
// bijectively to gold q through q = ~QN.
module DFFHQNx1_ASAP7_75t_R(input wire CLK, D, output reg QN);
    always @(posedge CLK) QN <= ~D;
endmodule
