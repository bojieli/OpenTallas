# FAN32 source v1 mapped census: rejected

Source2581fc2bb; standalone mapped ODB, no layout. Native census28 dynamic
>32 drivers, max53 (baseline3214, max281). No reset violation. All28 remain
blocking despite the reduction. Unplaced geometry and unbound PG are not judged.

First4000-cycle directRTL lockstep passed (ins2139/ovf2034/up173/tau1995).
Old PRE s_clr/s_v/s_b inputs were unkept and merged into new kept pin copies,
causing35/42 endpoint cones. Tail p_bg valid bits drove51 endpoints through
new replicated gt inputs. Six remaining combinational roots trace to original
shared GN count/compare logic. These are source fixes, not CTS-buffer fixes.
No gate, REVIEW or submission. Sourcev2 must pass an actual fresh census.
