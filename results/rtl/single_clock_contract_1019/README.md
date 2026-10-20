# Actual single-clock period contract

Gate-Rule change: an ordinary `cts`/`spine` tile may consume an explicit actual parent-clock period without inventing a multi-clock mode. Default profiles retain 833.333 ps. This opt-in requires equal route/signoff/actual periods, exact tile top/parameters/all source SHA256s, and full hashed native contract + GEN manifest + generated clock Tcl. The manifest must hash that same native contract, its domain period and exact entries must agree, and every instance of the named native consumer master must have exactly one scalar clock connected to the declared real source instance/output/domain. The generated Tcl must create that exact clock at that exact source/period. Missing, stale, contradictory or partial evidence fails closed.

Saved actual HBM BW safe4 source proof uses 64 native h9b controller clock entries, `hb_ckgen/pll_hbm`, period 1024 ps. The safe opt-in leaf is a successor to that parent master; the certificate separately binds its actual source bytes and parameters. This proves clock ownership, not functional equivalence or physical qualification. The committed raw GEN sources are unqualified die evidence, as their README states.

The existing bug gave the route real/link virtual clocks 1024 ps but recreated the signoff real root at the generic 833.333 ps. The FF/MM helper then synchronized the link virtual to that wrong real root. Consistent generation now keeps all of them at actual 1024 ps; registered runtime checks reject wrong actual roots and stale/mixed virtual periods before MM synchronization can hide them. Canonical replay ships and hashes every contract input. No uncertainty, false path, internal delay or repair margin changes. Boundary outside fractions remain 0.2/0.2 of the actual period (204.8 ps); interfaces keep existing skew/reserve/hold policy. Default 833.333 kits emit the same constraints.

Fleet unit `oth-ubuntu-3841881-1792427346`, ot-epyc4, OpenROAD 26Q3-1510-g6cb3f2b704:
- Actual 64-controller saved source/params/manifest/GEN clock positive PASS.
- Sixteen schema negatives PASS (wrong periods/root/port/count/hash/params/secondary clocks).
- Default 833.333 and unguarded override refusal PASS.
- Seven real OpenSTA cases PASS: TT actual/virtual1024 positive; FF/MM1024 positive; wrong real period, wrong virtual period, extra real root, unknown virtual and wrong FF/MM virtual all rejected with OT_SINGLE_CLOCK.
- Initial test harness missing technology LEF failure retained separately; it was corrected before any guard result was claimed.

No physical gate or BW kit adoption is claimed. ROOT review/baseline comparison/daemon helper sync must precede adoption. Apply the certificate to a fresh exact source snapshot and regenerate all kit/FF/MM constraints before a source-pinned gate. Existing wrong-constraint gates remain diagnostic evidence.
