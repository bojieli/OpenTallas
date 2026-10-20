# Private per-address random startup coupon — terminal failure

Actual fleet unit3183240-1792508652, 2026-10-20 08:05 PDT. No DUT interface, state machine, arithmetic, latency, shared SRAM/cell model, source mapped graph, clock, reset or stimulus chronology was changed. An owned reflink cache copy changes only34 generated SRAM constructor assignments (index-salted random initialization plus read-only logging), TB observer comparison threshold12→1, its banner, and an optional early-observer causal control. A private SV harness mirrors the observer change. This is explicitly reused generated-C++ instrumentation, not freshly elaborated output from that private SV source.

Only fast group0 and slow groups0/13/15 were rebuilt with the exact original compiler commands. Archive member SHA comparisons prove every other member unchanged. Runtime objects remain unchanged. Original mapped gold/candidate, canonical cell model, memory source and stimulus have exact source hashes in identity.json. First-class failure evidence is run_s3.log; no new mask or rerun was used.

| Seed | Observed edges | Result |
|---|---:|---|
|1|400|PASS;198valid, first79, post-reset122|
|2|400|PASS;191valid, first80, post-reset121|
|3|1|FAIL at cycle1 while rst=0, ov=1/1, differing payload/fault|

Every instance/address/seed combination is independently seeded. Actual constructor logs show1088 distinct64-bit words per seed and3264 distinct values across all three seeds (208896 bit identities). Initialization audit PASS does not turn the functional failure into a PASS. The wrapper exits0 after preserving rows; each row's rc and explicit verdict control qualification. Early-observer causal test was NOT RUN because the baseline did not pass all three seeds.

The failure occurs before the specified four-edge initial reset assertion has elapsed. The source consumer treats payload/fault as valid-qualified; ov is checked from the first sampled edge including reset, and data/fault whenever either ov is asserted. No cycle/reset/warmup exclusion is applied. The contract for public outputs during initial reset convergence requires ROOT review; this receipt leaves strict parent startup HOLD. Do not silently skip early edges, force state, or change reset/latency to relabel it.

Older mapped probes used one repeated random word per SRAM array because Verilator5.050 scoped RNG re-seeds on each call with the same per-array salt; they remain correlated-array-envelope receipts. Separate SVCRS KPV full/skew tests use another legacy binary and provide no mapped-startup qualification.
