# hbm_hcq_bank_cb_s1 (L2H-HC 10-19, H.STA.BLK.17)
Successor of hbm_hcq_bank_cb_1017. Its 07:30 --cts gate FAILED: pin-flop spread was 143/155 ps TT/FF, and trial GRT stalled for more than 4 h in incremental global_route (GATE_STALL 14400 s, rc 137). The old ring1 e2 route on ot-pve1 hangs in the same step.
Diagnosis: the 8 weight SRAMs sat in ONE abutted N-S stack (pitch 70.512, off the 43.2 lattice) with E-face pins (57 contacts/5.4 um). They faced the lane leaves' W faces across a 41.3 um channel. That channel is the congestion hot spot.
Redesign: 4 abutted SRAM PAIRS on the lane rows (y 43.2/216/388.8/561.6), with 31.8 um channels between the pairs. The SRAM E-face to lane channel is now 84.5 um: lanes at x302.4/475.2, x-SRAMs at x648 on lattice rows. The outline grows from 734.4x734.4 to 777.6x734.4 (slot_change_request; next die gen with claude/hc-ringplan-1019).
## SAFE-DESIGN checklist
1 Pins: as cb_1017 (HH-9 chain pin registers in RTL; reset landing per kit).
2 Reach: tile 777.6 um; lanes beside their SRAM pair (row-local).
3 Fanout: unchanged RTL; the gate lint will measure it.
4 Depth: unchanged RTL (gate depth 178 ps).
5 Storage: PASS - weights are in SRAM macros.
6 Floorplan: FIXED - macros on lattice rows (deliberate abutted pairs), channels >= 20 um, the pin channel doubled, aspect 1.06; fill ~47%.
7 Clock: the gate measures spread (old 143/155 FAIL); if it still fails, the next step is regional roots per lane-row pair.
8 Schedule: static; no cycle change.
