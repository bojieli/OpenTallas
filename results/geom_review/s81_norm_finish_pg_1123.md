# S81 norm_finish power-capable reference tile placement review

2026-11-23 15:13 PST. PASS-COND for a private CTS-only follow-up. The retained norm_finish LEF selected by J9 has neither VDD nor VSS pins and its provisional record borrows the ENG insertion value. This exact replacement is built from the existing norm_finish source and parameters NV80, K5, P3, D5120, LM5, LA6. It keeps the 181.44 × 190.08 µm outline and existing port boundary.

Viewed E10 `s81-j9-r6/compose/norm_finish_1451/actual/review.png` 62ab01266b31 from exact placed ODB 8d24311034e8. North pin banks seat their first register close to the edge, with median 4.95 µm and p90 6.57 µm. The rest of the tile has distributed soft-cell occupancy, no hard macro wall, 39.2% free-area fill, and 14% empty bins. The native readback found 33 VDD and 33 VSS terminal shapes on M5. Actual place and readback are E10 137358 and 472741, both exit zero.

Keep the selected J9 view held pending the replacement's native clock and route evidence, both timing corners, physical abstract export and parent strap contact. No new core view is signed.

## 15:26 PST exact CTS follow-up

HOLD. Viewed E10 `s81-j9-r6/compose/norm_finish_1451/cts_mm_1519/actual/review.png` 4c55925c0a5e from exact CTS ODB 494cf68f342c. The M5 power terminals survive (33 per net). The original first capture remains localized with p90 6.86 µm. Clock and hold buffers raised fill from 39.2% to 41.7% and create north-edge and interior local hotspots.

The first CTS continuation refused the absent synchronized FF scene. Fresh multi-mode run 566664 read exact TT and FF libraries with the same placed ODB. It wrote real CTS results despite two recovered RSZ-0060 hold chunk caps. At the 770 ps repair clock it has TT setup −90.067 ps across 34 endpoints, FF hold +9.738 ps with zero hold violations, and setup/hold skew 87.619/69.691 ps. The measured timing report identifies r[14] as a falling-edge output. Its 293.76 ps launch insertion traverses seven placed clock buffers, followed by 139.86 ps cell and escape delay. The north clock input at x11.772 and output-bank r[14] at x153.468 could use a much shorter northern intra-tile launch branch without changing the clock edge or adding a data cycle. The current route is held pending that branch seating and proof against its incoming launch-to-output-register paths. No GRT ran.
