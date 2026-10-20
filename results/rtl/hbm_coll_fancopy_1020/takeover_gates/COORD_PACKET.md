# COLL6 terminal gates: HOLD, no submission

Collected immutable gate_result.json, gate_layout PNGs and terminal logs from paused Claude WT. No REVIEW.json written. All four floorplan PNGs visually inspected by Codex.

| Kit | Gate | Native max | GRT overflow | TT setup ps | FF hold ps | TT/FF pin spread ps |
|---|---|---|---|---|---|---|
| n1s0 v74f | WARN | 32 | 0 | -19.1 | 44.2 | 57.4 / 55.0 |
| n1s0 v74g | WARN | 32 | 0 | -45.4 | 43.1 | 49.6 / 40.6 |
| n2s1 v74h | FAIL | 32 | 0 | -1.8 | 45.7 | 98.9 / 94.6 |
| n2s1 v74i | WARN | 32 | 0 | -1.1 | 44.2 | 36.9 / 35.9 |

TT timing is placement-RC pathfinding, not SS closure. Coordinator explicitly requires HOLD for negative TT setup. n2s1 h additionally fails clock spread. Preserve these failures; do not submit or bind.

Safe-design review: (1) PASS inherited registered pins/reset landing. (2) PASS planning outline maximum 345.6 um, no new long wires. (3) PASS actual pre-floorplan native census max32 all4; kept FANCOPY source. (4) HOLD estimated multiplier partial-product depth 652ps/18levels and negative measured TT slack; n1s0 f endpoint u_mul.pd[1][14], g protocol_fault, n2s1 h vm_req_sector[111], i inj_idx_pin[15]. Structural arithmetic/control pipeline required before successor, price added edge. (5) PASS four real SRAM macros, no new storage. (6) PASS inherited lattice coordinates, two macro columns with continuous cell channels, full-height W face 1709/1717 pins over345.6um =4.95/4.97pins/um; 259.2x345.6 or302.4x345.6 outlines. Fill25%/22% is pin-bound documented exception. Floorplan PNG shows no islands. (7) HOLD h spread; f/g/i pass spread but clock entry on W face requires retained parent boundary compensation. Insertion maxima TT434/487/476/451ps; hold margin0.03. (8) PASS FANCOPY adds0edges; inherited v74p +1 priced DS+474cyc/token.

Proof evidence already committed in proofs_r1/r2: 30/30 Verilator5.050, FC2 shift equivalence, production/dense tests and causal mvmc/mcopy/mlate mutants. Structural successor needs its own positive and causal-negative proof.
