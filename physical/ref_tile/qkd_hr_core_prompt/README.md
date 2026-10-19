# qkd_hr_core_prompt p7 (KV-RELAYGEN 10-19)

HOST root cluster child (KV / system die, MU release). p5 and p6 routes did not close, so p7 is a structural change, not a re-route:
gate p6 measured one reset relay flop per member driving 1,508 / 960 / 671 / 647 flops. p7 gives those members 7 / 5 / 3 / 3 kept
relay copies (`tools/qwen_kv_die/host_cluster/gen_prompt_rr.py`). The kit setting `reset_relay_split {max_loads 256}` then spreads each
member's reset loads over its copies during synthesis (`physical/common_flow/ot_rst_split.tcl`).

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|------|--------|
| 1 | pin registers + 2-stage reset landing | PASS: pin_regs on (all data pins, host_rst_n included); por_n lands in 2 stages (reset_landing); each host_rst_n member relay is 2 sync + 1 kept relay stage |
| 2 | reach <= 405 um a cycle | PASS: the outline is 280.8 x 280.8 um, so no wire inside the tile is longer than one hop |
| 3 | fanout <= ~32 in critical cones; reset copies <= 256 | FIXED in p7: relay copies stay at or below 256 loads (ot_rst_split.tsv in the synthesis results; the gate's textbook high_fanout is the independent check); the copies are kept cells |
| 4 | depth <= ~600 ps / 20 levels a stage | PASS at p6 RTL: the p5 classes were fixed in p6 (SECDED per-slot decode, look-ahead counters); the p6 gate placement reg->reg was +7.9. Watch the p7 gate |
| 5 | storage > 2 kb in SRAM | PASS: 5 SRAM macros (1x 1024x256, 4x 256x64) |
| 6 | floorplan | macros sit on the 43.2 lattice in one abutted N-S column, with pins on the W/E faces only and a 5.4 um halo. WAIVE util ~16 % of free area: the outline is set by the pins (5,439 pins, about 5.8 pins/um on W/E), not by area |
| 7 | clock | PASS: ck_core is at the centre of the S face; p6 pin-flop spread was 45.8 TT / 41.3 FF (limit 80); io_hold_margin_ns is 0.03 |
| 8 | static schedule | PASS: 0 cycles. The copies sit inside the existing +3-edge reset release, and all copies release on the same edge |

Equivalence: the copies are identical registers, and ot_rst_split.py checks that for each bit before it moves any load. The smoke
test `results/arch/kv_relaygen_1019/smoke` passes SAT-induction equivalence against the unsplit netlist, and its mutant fails.
