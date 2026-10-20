# PV join pin-bound plan (model only)

The 172.8 um square candidate fails the conservative total pin-density rule on every face: E 1542 pins / 166.848 um = 9.242/um; W 1031 / 164.016 = 6.286/um; N/S each 1024 / about164 = 6.244/um. Splitting layers does not repair the total-density failure. No REVIEW or submit is permitted.

Preserving the production faces and at least4.32um edge margins requires usable E height>=257um, N/S width>=170.667um. A 216 x280.8um outline gives E5.665,W3.788,NS4.938pins/um and diagonal354.3um. Clock goes at the W midpoint adjacent to a centered contiguous standard-cell region. There are no SRAM macros in this join. Source remains2882c6196, native census32, zero token cycles and accepted+2boot edges; all physical timing/reach must be remeasured.

This is pin-bound: placed standard area14127um2 / core58525.2864um2 is24.14%, so the40-60% utilization target cannot coexist with the fixed faces without an explicit pin-bound cost exception. An outline that fits the old utilization cannot fit the required pins.

The actual current GEN9 snapshot75171867d (gen9d9q) has two PV pair frames1555.2 x12009.6um,32joins per pair. Join growth forces each3x3 block561.6square to at least604.8 x669.6um. Holding all existing channels/gaps makes a pair at least1641.6 x13737.6um, adding1728um height. At pvw_0's fixed y56.16 the new top13793.76 crosses the AHUB origin12238.56 by1555.2um. The64join tile area cost is+1.970mm2; whole pair-envelope growth is+7.749mm2 across two pairs (geometric lower bound). Therefore this shape DOES NOT FIT current GEN9. Parent placement/trunk stages and token schedule must be recomputed before any gate/adoption, with costs recorded in the system model.

A source restructuring or a joint die replan is required. Current172.8gate remains immutable diagnostic evidence. This packet authorizes no new shape, exception, gate, or submission. Exact inputs/calculations and captured GEN9 identities are in PIN_BOUND_PLAN.json and gen9_geometry.json.
