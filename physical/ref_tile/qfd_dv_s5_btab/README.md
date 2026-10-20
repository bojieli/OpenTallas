# qfd_dv_s5_btab -- slice2 VM leaf (QW-VM8SPLIT r2, COORD 09:45 split decision)

QW-VM8SPLIT: vm8 split into single-root leaves (COORD 09:45); this leaf = BTAB SU copy (column of 4 x 128x256; r2: r1 2x2 302.4-wide S face spread 107 ps).
RTL `rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv` (top `qfd_dv_s8x_btab`), specs `tools/qwen_dv/s5_vm8x_kit.py`. Partitions (zero signals cross
between leaves): P1 = vmr x3 + crom + btab + prog (SPLIT 1); P2 = vmr x3 + crh x2 + btab + prog (SPLIT 2, parallel fallback).
r1 lesson: leaves 302-475 um wide on the dense S (tw / write) face -> S-face pin-register ends 130-237 um from the S-centre
clock pin, TT pin-flop spread 107-146 ps (crom 140.7, su 145.9, btab 107.1); vmr / prog (259.2 wide) 55.7 / 38.2 PASS.
r2: every leaf <= 259.2 um on its dense face, single macro column.

## Pre-gate native census (mapped ASAP7 RVT TT + macro TT libs, openroad/orfs, fleet)
qfd_dv_s8x_btab: PASS, 0 drivers > 32 (ports + reset included), max 16 loads, 3441 FF, std area 1181.9 um2 (macro/pin-bound,
fill_reason recorded), no latches, no ties.  Evidence results/arch/qw_vm8split_1020/native/qfd_dv_s8x_btab/census.json.

## Bench (V5.050): composition qfd_dv_s5_vm8x vs qfd_dv_s5_vm7 with vm8 priced delays
SPLIT 0 / 1 / 2 PASS 59,620 compares / 0 mismatches each; mutants (SPLIT 2) coll 12,357 / wpri 31,372 / bsel 59,587 FAIL.

## Safe-design checklist
- 1_pins: PASS: RTL registers every input and output at its pin (= vm8 pin registers); rst_n lands rl0 -> rl1 and resets only the sticky fault; no combinational pin arc
- 2_reach: PASS (by floorplan): outline 259.2 x 354.24, every pin <= 354 um from any sink; gate wire_reach checks 405 um
- 3_fanout: pre-gate mapped census results/arch/qw_vm8split_1020/native/<top> (kept copies as vm8)
- 4_depth: PASS: = vm8 (census depth recorded); no logic before a macro pin except the 2-register collision compare
- 5_storage: PASS: all > 2 kb state in SRAM macros
- 6_floorplan: PASS: x on 43.2, y on 8.64, macro channels >= 20 um, S band 86.4, aspect 1.37, faces E 281 / 354.2 = 0.8/um, S 1,069 / 259.2 = 4.1/um
- 7_clock: ONE CTS root (S-centre ck) over the whole leaf = one region; pin-flop spread <= 80 TT+FF judged in the gate; every crossing to a slice2 neighbour lands in a parent mesochronous ring; io_hold_margin 0.03
- 8_schedule: static; 0 edges vs vm8 (reads 2 -> 4, VM write -> read 1 -> 3, tw +2, fault +1 = vm8b prices)
