# QC-PG-3 (2026-10-28): QC A0 window on MEASURED A0 power, 150-um bumps -> FAIL; 75-um / G12 pass

Successor of QC-PG-2 (claude/qc-pg-2-1028@037cd941d3). Open term there: the A0 window passes iff A0 total <= ~0.62 W/mm2.
Deck/method unchanged: QC-PG-MAP upper deck (M9 .672, 150-um bumps / 70-um pads, R35 plan), exact linear class superposition
(A = A0 tiles, F = flattened logic, S = signed cores), VDD drop + VSS bounce co-located per load block, 450-um window edge
excluded, A0 below-M7 = 4.597 mV budget (no A0 own view). tools/pg_activity/qc/a0_superpose.py generalises su8_superpose2.py
to any kit tag and an A0-only window; it reproduces QC-PG-2 20.397 (A0 0.417) and 29.073 (A0 0.60) exactly (CHECKED).

## 1. A0 NK tile power, same CTS databases as Codex qc-a0-activity-0359 (TT, placement RC setRC_rcx, propagated clock)
Power = report_power with register outputs + inputs annotated (tools/pg_activity/qc/power_act.tcl; unmatched -> 0).
FLOOR = every data activity 0, clock running (A0 has NO clock gating: 0 ICG cells in the parent and rawleaf netlists,
none in the tile / leaf RTL). All runs EXIT 0 (CHECKED as run outputs; power/*.rpt).
| child (x per NK tile) | floor mW | production BUSY mW | basis of BUSY |
|---|---|---|---|
| rawleaf lane slice (x8) | 27.434 (clock 12.457 + seq clock-pin 14.944) | 57.992 | RTL sim, bench/tb_rawleaf_prod.sv: v_d every cycle, INT8->BF16 weights, BF16 x new each cycle; gate-level netlist, 12030/12030 FF QN nets mapped (map_qn.py), 192 input-anchor FFs at 0 |
| romleaf (x10; 2 read per cycle) | 13.934 (ROM macro 8.945 unconditional Liberty clock power) | 16.018 active / 13.934 other-bank | RTL sim, bench/tb_romleaf_prod.sv MODE 1 (ce every cycle, sequential rows, random image) / MODE 2; 2200/2200 regs matched |
| node (x1) | 25.310 | 69.148 (Codex stress, n_va 75 %) | upper bound, not production-measured |
| NK parent glue (15,032 regs, 86.9k cells, QC-A0-KITS-3 default-CTS trial) | 51.431 (clock tree 32.435) | 91.227 (every reg/input 0.5) | upper bound (no parent RTL replay) |
| **NK tile (0.5302 mm2)** | **435.56 mW = 0.8216 W/mm2** | **767.82 mW = 1.448 W/mm2** | |
The floor alone is 1.33x the 0.62 W/mm2 pass threshold. Codex's 0.417 W/mm2 floor counted only the Clock group + ROM;
the sequential clock-pin internal power (rawleaf 14.9, node 15.3, romleaf 2.8, parent 18.9 mW) and the parent's own
15k-register clock tree (32.4 mW) are activity-independent too.

## 2. Production duty (who is active per token)
Qwen3-8B TP8, 768 A0 tiles x 64 MAC lanes, one ROM row (2 x 32 INT8) per busy cycle. Per layer per tile:
qkv 64 + o 43 + gate/up 256 + down 128 = 491 busy cycles; LM head 1,583; per token 19,245 busy cycles of 296,341
(composer q_nc_none_land, results/qc_sliceclk_1027/price) = 6.49 %. Consistency: the ROM (768 x 10 x 4096 x 32 INT8 =
1.007 G) is 94 % filled by the 946 M weights a die holds, each read once per token (1 user). Within windows: gate/up 256 of
a 537-cycle span (48 %), LM head 1,583 of 3,135 (50.5 %); every tile is busy for up to 1,583 consecutive cycles (1.3 us),
long against the package/bump time constants, so a static solve should not average over the token. (ESTIMATE from the
shapes + composer spans, consistent with the ROM fill; not a die replay.)
P(d) = floor + d x (busy - floor): d 0 -> 0.822, token 6.49 % -> 0.862, window 50.5 % -> 1.138, burst 100 % -> 1.448 W/mm2.

## 3. A0 window re-solved (superpose.jsonl; upper + 4.597 below-M7; F 0.27 as QC-PG-2)
| deck | A unit mV per W/mm2 | floor 0.822 | token avg 0.862 | window 1.138 | burst 1.448 | verdict |
|---|---|---|---|---|---|---|
| current .672, 150 um, A0 window (cb array, u_b49_52) | 48.14 | 44.50 | 46.46 | 59.74 | 74.68 | FAIL at every basis, incl. zero data |
| same deck, SU-window A0 edge (u_b49_12) | 47.76 | 44.22 | 46.15 | 59.33 | 74.15 | FAIL (agrees with A0 window +-0.4) |
| 75-um bumps / 37.5 pad, grid unchanged (B75, SU-window A0 nodes) | 16.41 | 18.08 | 18.75 | 23.27 | 28.37 | PASS at every basis |
| G12 grid (M8 .48@4.32 + M9 12.96@34.56), 150 um | 17.48 | 19.05 | 19.76 | 24.58 | 30.01 | PASS at every basis |
| C3 grid (M8 .48@4.32 + M9 6.48@34.56), 150 um | 28.68 | 28.62 | 29.79 | 37.70 | 46.60 | PASS only on token average |
All solves are the QC-PG-MAP kits (CHECKED as solves); the B75/G12/C3 A0 numbers use the SU window's 5 south-edge A0 tiles
(no A0-window kit for those decks): ESTIMATE that they hold in the dense A0 array (on the current deck the two windows agree
within 0.4 mV). Pass limits on A0 density: current 0.62, C3 ~1.0, G12 ~1.7, B75 ~1.85 W/mm2.
su8 window (QC-PG-2 32.24 PASS) has zero A0 sensitivity and is unchanged.

## 4. Reading
QC fails 35 mV at 150 um in the A0 array on measured A0 power, and it fails on the activity-independent floor alone
(44.5 mV), so no activity refinement can close it. Levers: (a) 75-um bumps (0 tracks, 4x bumps), (b) G12-class grid
(M8 2x + wide M9 -> breaks the R35 M8 pair-row clock reservation, re-plan), (c) design: A0 clock-floor reduction
(per-tile clock gating does not help the burst basis; ROM macro clock power is 0.169 W/mm2 of the floor; even with it
removed the floor 0.652 > 0.62). -> OWNER? (75-um) posted, per owner rule 10-27 (75 um only if 150 still fails).
Not measured: node and parent production activity (upper bounds used for BUSY; the floor result does not depend on them).
