# HBM current live gate pickup, 2026-10-19 13:37–13:39 PT
Read-only pickup; no synthesis, routing, rerun, review, or submit launched.

| Exact vehicle | Actual state |
| --- | --- |
| k9s2 3b6517288, client533619, ep4 hbm_sfucore_k9-20261019-120005 | Live GPL OpenROAD1061994 at99.9%CPU; latest log stopped at pre_global_place_io_flop_at_pins. Not CTS complete. Original reset6245/native safety debt remains. |
| k9r e0a1c790e, shell1194869/python1194873, ep4 hbm_sfucore_k9r-20261019-123227 | Live GPL container3588968; exact source/native fanout proof still required. |
| GQ k1/k2 b523b57db, clients76470/79334, ep8 hcoll_gq_issue_k{1,2}_1019-20261019-11275{5,6} | CTS complete, live GRT extra congestion iterations. k1 boundary TT168.9/FF162.3ps FAIL. k2 boundary76.5/67.1ps; all endpoints124.2/101.5ps and SRAM native reference unknown. No closure or SAFE claim. |
| PGSAFE2 23910522d, client1311539, ep8 hbm_su_pg_stream_b_safe2_1019-20261019-121732 | CTS OpenROAD1498005 live244%CPU; original stale JSON not current verdict. Native78b77c1ff HOLD3roots42/596input42output logic remains. |
| e86 startc4978a219, submitclient911162 | Terminal13:20 WARN then actual local submit REFUSED REVIEW_REQUIRED: geometry736bd3eb8b7a→f52e67dd19c3. Not submitted/running. |

E86 exact snapshot archive eb58e463f96b0e8918901fd92dada1db405ad58330930eda135c4b753605bca6, manifest9d4cc3fa1feebd31a661e9c587a71ff93b5df2f65a5b15f8c9c5a41d0b923da3. Native ep6 run `/srv/opentallas-scratch/claude/ref_gate/hcoll_v7_tkm_tile_e86-20261019-115537` final trial GRT ODB SHA fe1ac40239ac2a16456debd95ab95e220ff29772011babc3bc8f80e166ff010c. CTS SSsetup+2.38/FFhold+25.01ps precede GRT. GRT related synchronous seam max−11.551648ps r0→r1,−11.083135 r1→r2,−6.277590 r2→r3. Log loads WC(mode ss)/BC(mode ff); these are retained as raw seam evidence, not claimed as TT qualified signoff. GRT0 overflow; clock worst reported boundaryTT28.1/FF26.7, other root boundary47.7/42.1; WARN utilization42.7%. No final TT setup/FF hold signoff or electrical/fanout/PG safety qualification. Full native all-driver BUF/INV-transparent <=32 source-bound proof, registered pins/reset/reach and PG conductor proof remain open; older2064root negative must not be silently transferred to a changed snapshot.

Critical PNGs for root personal review, no REVIEW written: `/home/ubuntu/artifacts/hbm-live-gate-terminal2-1019/e86_floorplan.png` and `e86_density.png`. Geometry/lattice/pin density/placement safety has not been newly assessed in this pickup; geometry refusal plus structural/native debt precede any submit. No reopening unchanged failed route.

`ep4.txt`, `ep8.txt`, `e86_remote.txt` contain bounded original log/clock receipts; `e86_gate_result.json` and `e86_regate_submit.log` are byte copies. Runtime per-row source/main changes are not applied to frozen live runs.
