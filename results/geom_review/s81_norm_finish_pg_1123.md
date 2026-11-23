# S81 norm_finish power-capable reference tile placement review

2026-11-23 15:13 PST. PASS-COND for a private CTS-only follow-up. The retained norm_finish LEF selected by J9 has neither VDD nor VSS pins and its provisional record borrows the ENG insertion value. This exact replacement is built from the existing norm_finish source and parameters NV80, K5, P3, D5120, LM5, LA6. It keeps the 181.44 × 190.08 µm outline and existing port boundary.

Viewed E10 `s81-j9-r6/compose/norm_finish_1451/actual/review.png` 62ab01266b31 from exact placed ODB 8d24311034e8. North pin banks seat their first register close to the edge, with median 4.95 µm and p90 6.57 µm. The rest of the tile has distributed soft-cell occupancy, no hard macro wall, 39.2% free-area fill, and 14% empty bins. The native readback found 33 VDD and 33 VSS terminal shapes on M5. Actual place and readback are E10 137358 and 472741, both exit zero.

Keep the selected J9 view held pending the replacement's native clock and route evidence, both timing corners, physical abstract export and parent strap contact. No new core view is signed.
