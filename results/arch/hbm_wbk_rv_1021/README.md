# WBK read-valid selector repair

Source451867fe3 uses the kept payload-selector copy rtd for both the FIFO payload mux and its read-valid selection. The prior structural CDC proof found an empty-slot read in the rtc != rtd cone. The copies are equal in normal operation; choosing the same physical copy makes the local storage/valid implication explicit without changing data or credit ages.

The actual repaired canonical GEN passed at20:33:50 PT, with an unaltered keyed lint receipt, 50m20.94s wall time and4,856,992KiB peak RSS. Three production-shaped positives passed8blocks/5,563sectors/1,920group requests; all nine required causal mutants were rejected. The per-PP counterexample passed with9grants/A4/B3; pooled-counter M11 was rejected. The exact repaired RTL hash agrees between source, GEN and bench snapshots. Raw logs and hashes are retained here.

Native synthesis is running on the canonical published453 helper, native_census SHA4e7a7a425a8669a5f586ed3aa2873038e727293a9128aabae360fcbaa2cd61e0, with the indexed lint SHA2ed19e2e080edf41f275088ce50ed9a3ac1b05b246e6ccfb79d81eca1871a94b. A fresh run received only the exact repaired RTL, SOURCE_COMMIT and unaltered actual GEN receipt; normal GEN naturally validated it before synthesis. No forced identity or mapped-netlist override. Native32, physical timing/area, external calendar and actual die adoption remain OPEN.

NEXT: actual native PASS32/role0 and no-layout marker, then physical MAIN+FALLBACK gates. Old0441 failing/stopped source evidence remains distinct.
