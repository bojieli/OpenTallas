# QC UCIe bounded source repack, 2026-11-01

Picture: `results/qc_die62_1101/codex_ucie_repack_1101/source_repack.png` (personally viewed).

Verdict: **BLOCKED_G0C_BIND_CLOCK_BOOT_EVENT**. Three types and the die edge are preserved. Both shared coll_ft replicas and coll_core move east25.92um and narrow by25.92um; UCIe receives the released strip. No new footprint overlap or native macro overflow remains. The25.92um gap beside coll_f1 is explicit and needs parent corridor/clock/PG review. Interior peer macro homes stay fixed.

The shared FT reset face terminal moves655.20→633.632um, and its collector data/control/forwarded-clock pins move together. The source monitor hop census includes ready, fault and forwarded clock; maximum across the whole die384.128um. Changed core→f3 hop267.968→293.888um remains below405.

Widening UCIe crosses the default400um grid threshold:10→15 normal clock inputs, reset relay depth3→4, release after pin4→5cycles. This adds one local boot cycle (833ps) and no mission data stage. The source model records this; the composed parent clock/START programme remains held. Old failed remap and unpriced-depth rejection receipts remain immutable.

No new GEN/P&R/STA/proof or physical release. Whole G0C differential and strict native bind are pending. The matching PHY view remains an assumed licensed abstract.
