# SRAM bank64 external escape diagnostic

ROOT personally viewed the floorplan/density PNGs of exact geometry
`5c75a1978a78c3943f0d66594d802194c89ae40951250b7bc8b3df730294902c`
and authorized diagnostic routing after current exact gate binding.

The 108 x 108 um harness contains one real analytical 32x64 dual-clock macro
at 43.2 / 43.2 um, raw area 553.590 um², with unchanged 206 signal/clock
contacts, 0.096 um local pitch and approximately 10.49 contacts/um active
span. Full-face density 5.952/um is not external access qualification.
No contacts, obstructions, power pins or clock timing models are simplified.

The low utilization and distributed harness pin registers are explicitly
accepted only for this escape experiment. This is not a production floorplan,
area estimate, clock-compensation contract, repaired-memory substitution or
CDC proof. Both memory clocks share one synchronous harness clock.

Original gate source e26d92503 had GRT overflow 0, 206 accessible boundary
pins, 206 FFs and maximum exact mapped scalar Q/QN data fanout 1. Native CTS
probe measured launch 93.789 ps and capture 70.548 ps, no combinational
boundary paths, TT/FF pin-flop spreads 20.5 / 18.7 ps. Macro clock slews were
13.1 / 13.3 ps TT and 10.9 / 11.1 ps FF. Placement timing is diagnostic;
the original +42 ps hold result is not represented as routed FF hold.

A direct source-level coupon test exercises all 32 rows, partial writes,
read-enable retention and 1,392 read comparisons. Verilator 5.050 positive
passes and an inverted write-mask mutant fails ESCAPE_MISMATCH. This
qualifies the access-test mechanism, not independent-clock collision/CDC.

The next route must preserve actual signal/PG geometry, test pin access,
PG connectivity, vias, minimum area and full detailed DRC, and collect
TT setup / FF hold with native boundary data. A failure remains a failure
and requires a structural successor, never a cosmetic LEF stretch.
