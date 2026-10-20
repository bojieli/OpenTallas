# PS2 cold state audit: FAIL

Independent copied-FF convergence SAT passes 395 pairs with twelve assertion/release half steps each. The shared arbitrary macro output model proves only copy convergence, not macro-state or RTL equivalence.

The earlier real-SRAM miter randomizes eighty original registers with added copies, pairs their COPY0 states, independently randomizes 395 added registers, and pairs arbitrary physical arrays and rd_out for all seven macro pairs. Seeds 251 and 523 pass 20,000 cycles each. Seed 997 fails at cycle21: prompt macro u56130_c0.u_cell array row0 differs. The payload mutant was never reached.

A full-inventory run randomizing all 16,012 original/COPY0 register pairs passes seed997 for100cycles. Its RNG schedule differs, so it does not refute the preceding counterexample. Its immutable final stdout inherited an incorrect six-seed/120k/mutant summary; ONLY the 100-cycle one-seed receipt is supported.

An exact replay explicitly initializes every one of the 16,012 original/COPY0 states: 15,932 are explicitly zero, eighty follow the historical RNG stream, and the 395 added states remain independent. All seven arrays and rd_out are paired arbitrarily, with no repairs. It reproduces the failure without relying on simulator defaults. At the FIRST rising edge (5ns), original prompt w_ce_in=0 while candidate=1; original wd_in=0 while candidate has repeated 00803f40 payload. Row0 then remains different at cycle21. Cold landing converges later and cannot restore SRAM contents.

The source, scripts, source-pinned original/retained mapped netlists, raw pass/fail logs and initialization manifests are retained. This is a hard qualification failure; no layout adoption, warmup mask, ignored row, or inferred unobservability is authorized. A private new reset contract that inhibits all seven macro reads and writes on both newly changed reference and candidate is separately prototyped and cannot inherit plain-reset admission.
