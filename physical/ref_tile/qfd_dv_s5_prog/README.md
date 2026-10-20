# qfd_dv_s5_prog -- slice2 VM leaf (QW-VM8SPLIT, COORD 09:45 split decision)

QW-VM8SPLIT: vm8 split into single-root leaves (COORD 09:45); this leaf = fallback partition: PROG 2 banks x {lo, hi} (column of 4 x 256x256); no reset, no fault.
RTL `rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv` (top `qfd_dv_s8x_prog`), specs `tools/qwen_dv/s5_vm8x_kit.py`. Partition (zero signals cross
between leaves): vmr x3 + crom + su (primary); fallback = su replaced by btab + prog. One CTS root per leaf (S-centre ck).

## Pre-gate native census (mapped ASAP7 RVT TT + macro TT libs, openroad/orfs, fleet ep7)
qfd_dv_s8x_prog: status PASS, 0 drivers > 32 (ports + reset included), max 16 loads, rst_n n/a (no reset) loads,
3291 FF, std area 1150.3 um2 (fill 1.3% of 259.2 x 354.24 -- macro-bound leaf), no latches, no ties.
Reach: outline <= 354.24 um; storage > 2 kb only in SRAM; every pin registered in RTL.
Evidence results/arch/qw_vm8split_1020/native/qfd_dv_s8x_prog/census.json.

## Bench (V5.050, rtl/test/qwen_dv/s5/vm8x/bench.sh): composition qfd_dv_s5_vm8x vs qfd_dv_s5_vm7 with the vm8 priced delays
SPLIT 0 PASS 59,620 compares / 0 mismatches; SPLIT 1 PASS 59,620 / 0; mutants coll 12,357 / wpri 31,372 / bsel 59,587 FAIL
(witnesses results/arch/qw_vm8split_1020/bench/run_*.log).

## Safe-design checklist
- 1_pins: PASS: RTL registers every input and output at its pin (= vm8 pin registers); no reset (datapath only); no combinational pin arc
- 2_reach: PASS (by floorplan): outline 259.2 x 354.24, every pin <= 354 um from any sink; gate wire_reach checks 405 um
- 3_fanout: pre-gate mapped census results/arch/qw_vm8split_1020/native/<top> (kept copies as vm8)
- 4_depth: PASS: = vm8 (census depth recorded); no logic before a macro pin except the 2-register collision compare
- 5_storage: PASS: all > 2 kb state in SRAM macros
- 6_floorplan: PASS: x on 43.2, y on 8.64, macro channels >= 20 um, S band 86.4, aspect 1.37, faces E 467 / 354.2 = 1.3/um, S 926 / 259.2 = 3.6/um
- 7_clock: ONE CTS root (S-centre ck) over the whole leaf = one region; pin-flop spread <= 80 TT+FF judged in the gate; every crossing to a slice2 neighbour lands in a parent mesochronous ring; io_hold_margin 0.03
- 8_schedule: static; 0 edges vs vm8 (reads 2 -> 4, VM write -> read 1 -> 3, tw +2, fault +1 = vm8b prices)
