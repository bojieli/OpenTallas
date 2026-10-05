`timescale 1ns/1ps
// Standalone assumption witness, NOT a WINDOW stale-identity detector.
// Observer identities are separate from identical epoch/sector/beat/payload.
module tb_provider_fence_ghost;
 parameter bit VIOLATE_FENCE = 0;
 logic [63:0] old_operation=0, new_operation=512;
 wire [278:0] old_wire={17'd65543,4'd0,256'd123,2'd0};
 wire [278:0] new_wire={17'd65543,4'd0,256'd123,2'd0};
 wire deliver_old = VIOLATE_FENCE;
 initial begin
  #1;
  if(old_wire !== new_wire) $fatal(1,"ghost witness fields not identical");
  // Correct provider excludes old delivery. Deliberate lying fence cannot
  // be made safe by a1bit token or by expecting WINDOW to infer hidden ID.
  if(deliver_old && old_operation != new_operation)
   $fatal(1,"FAIL_PROVIDER_FENCE_ASSUMPTION_VIOLATION; NOT_WINDOW_DETECTION");
  $display("CLOSED_PROVIDER_ASSUMPTION_CHECK_ONLY; NOT_SOURCE_PROOF_OR_RTL_QUALIFICATION");
  $finish;
 end
endmodule
