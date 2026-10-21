# hbm_su_qcore_r13_1020 -- qcore r13c in the r6n outline (DRIVE-HBM/HBM-QCORE9, 10-20)

RTL ot_hbm_su_static_qcore_r13 (claude/hbm-qcore9-1020) = r12 + Codex FP6 ot_hdc_fp32_add_n32 adders (d73bee5f7; pretree x7 +
reducer) + per-writer bank-hit compare + 1-bit reset ports per reset flop + reducer kept enable/select/max copies.
Same ports/edges/function as r5..r12. Kit-scoped synthesis option: spec orfs_vars SYNTH_CANONICALIZE_TCL = synth_canonicalize.tcl
(Codex alias + splitter flow, copy_aliases.py kit copy; graph-verified aliases, then the unchanged ot_rst_copies.tcl).
Native census on the gate's mapped netlist: r12 189 violations/max 135 -> r13a 29/129 -> r13b 11/95 -> r13c PASS max 32
(results/rtl/hbm_qcore9_1020/census). Reset landing 24 copies, 15/copy (ot_rst_copies.tsv).
Benches (Verilator 5.050): lockstep vs r5 PASS checks=9104, MUT256 FAIL; pretree m0 PASS, m512/m1024 FAIL (results/rtl/hbm_qcore9_1020).

SAFE-DESIGN checklist (owner 10-19; guidance under the 10-20 09:35 rule freeze):
1 Pins: PASS -- keep_pin_regs/io_flop_at_pins; reset lands in 2 stages (OT_RST_LAND), 24 landing copies.
2 Reach: PASS -- 280.8 x 280.8 tile, every path < 405 um.
3 Fanout: PASS -- native census max 32 (r13c), FP adder internals via FP6 copy families, kept copies verified by the census.
4 Depth: as r6 RTL (per-sector decode, gated k+1 read registers); gate --cts reports the worst classes.
5 Storage: WAIVED (rule freeze) -- 8,192 b flop RF in 8 sector modules (1 kb each); reduction lines in 2 SRAM macros.
6 Floorplan: PASS -- 2 SRAMs on the 43.2 lattice, outline = closed d4g slot 280.8 sq, util ~0.3 (pin-bound W/E faces).
7 Clock: single centre root on a 281 um tile; gate must show pin-flop spread <= 80 TT+FF; io_hold_margin 0.03.
8 Schedule: static; 0 edges added over r5 (write-conflict fault at k+2, status only).
