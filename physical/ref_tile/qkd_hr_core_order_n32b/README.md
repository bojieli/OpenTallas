# qkd_hr_core_order_n32b — UNRENDERED structural candidate

No gate before ROOT exact source_native registry adoption. Source and copy-state proofs PASS; final placement/clock/route OPEN.

{
  "1_pins": "SOURCE PASS: inherited registered boundary and exact two-edge reset forest; actual balanced12/288 proof PASS. ROOT source_native interface not yet adopted.",
  "2_reach": "PLAN PASS: pairwise bound on all macro/band terminals 395.239um<405; actual placed/net reach OPEN.",
  "3_fanout": "MEASURED PASS: all69134 drivers maximum32, zero violations, resets included; no SRAM duplicated.",
  "4_depth": "S2 historical native575.1ps/14levels; copy transformation adds no levels, actual gate setup/hold OPEN.",
  "5_storage": "PASS: six real32x128 SRAMs for two >2kb runtime-indexed FIFO payloads; remaining runtime arrays below2kb.",
  "6_floorplan": "PLAN:43.2lattice six macros; full-width std band y216..300.24; measured source area11773.81656um2, modeled density0.410; physical row hook probe PASS; final placement/PG/pin escape OPEN.",
  "7_clock": "STRUCTURAL REDESIGN: all core and boundary registers in north band, no south pins; north centre clock; TT/FFspread<=80 required, not yet measured; io_hold0.03.",
  "8_schedule": "No added edge; SRAM capacity/II1 preserved; V5.05012000cycles PASS/2source mutantsFAIL; all extraFFcopies share literalDandclock, independent4state canonicalcoupon PASS afterfirstrealclock withoutasync2sync/memoryabstraction."
}
