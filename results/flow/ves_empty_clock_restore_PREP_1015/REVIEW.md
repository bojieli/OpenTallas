Source-only proposal; no VEs timing or generic clock-RC qualification.

The optional empty-driver profile keeps each unloaded native CLOCK net in the complete original graph identity. It permits only the explicit selected BUFx24 A/Y master, exact instance/input-source/root join, one native OUTPUT, no BTerms, no route wire, and native root-only fanin from a real clock source. Missing, extra, loaded, wired, foreign-root, wrong-pin/master and malformed profiles refuse. The existing full clock master/pose/connectivity/wire comparison remains mandatory before the checked CLOCK-only RC restore.

The G2 consumer now records global_routing_frozen_clock honestly only after the checked restore returns and emits its verified marker. Gate and policy scene modes must agree, and TT/FF must use the same mode. This neither supplies nor qualifies a CLOCK-only SPEF subset. The caller must stage the immutable source/profile/clock-only dataset and data-exclusion identity packet before any native use.

Validation: 11 Tcl shape/root controls and40 relevant existing/new G2 policy controls pass. One unrelated legacy generator fixture cannot run in this sparse checkout because its source file is absent. No native process, old DATA SPEF reuse, gate waiver, scene relabel or VEs retry was performed.
