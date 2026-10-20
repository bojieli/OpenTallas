# qfd_tile_nl_romleaf_rc8b — QW-A0-RC4 rc8b (10-20), CRITICAL (A0 feeds CB16)

rc8b = rc7b floorplan (outline 820.8 x 907.2, 19 hard children on the 43.2 lattice, pins/hub/tx fences unchanged) +
REGROOT 8 RTL (rtl/hdc/ot_qwen_w12_matvec.sv, ot_qwen_rom_tile_w12.sv; branch claude/qw-a0-rc4-1020 @3fe36bf2e) +
the engine input register stage (go_q, 28 go copies, ib_q, first xl stage; clock ck) boxed in the east channel beside
the tap pins (land_ib 784-816 x 86.4-820.8), so the ck_fa4 -> ck crossing is a short register -> register hop
. Generator tools/qwen_romleaf/rc8/gen_rc8.py. No REVIEW.json / submit: gate PNG + checklist via lanes/COORD-REVIEW-QUEUE.md.

Why: rc7 gates (results/arch/qwen_a0_rc4_1020/rc7_verdicts.txt) failed only cross_clock, and the binding Codex
mapped census (4339f2773) failed NK 262 / NL 291 loads; native_census.py on the rc7 netlists: NK 103 / NL 104 drivers > 32.

## PRE-GATE NATIVE CENSUS (tools/ref_tile/native_census.py, actual RVT TT Liberty, mapped 1_2_yosys.v of the r4 gates)
NK rc8 / rc8b: PASS, max 32 loads, 54,478 roots, 0 violations, 0 role errors; NL rc8: PASS, max 32, 51,397 roots, 0 / 0
(results/arch/qwen_a0_rc4_1020/census_*_r4.json.gz). Iterations: r1 NL 47 / NK 48 (max 54/52), r2 18/18 (max 84),
r3 NK PASS / NL 1 (34), r4 PASS. Reset nets included (16 kept landing copies, <= 32 each); constant outputs = tie_hi/lo only.

## Safe-design checklist (pre-gate; layout facts from the gate PNG/json are added in the review packet)
1 Pins — PASS: every data pin registered at its face (tap/tile_id ck_fa4, n_a/n_b ck_fa0/1, outputs ck_fa2/3); reset
  lands in 2 kit stages on ck with 16 kept last-stage copies (reset_relay_split <= 32).
2 Reach — FIXED by floorplan as rc7 (W pins -> node 388.8 um; hub <= 385 um from E pins; ROM->LSL landed rungs).
  REGROOT 8 adds no long hop: rung 0 still captures in its tx fence; leaf fault pins land on clk (FREE, beside the LSL).
3 Fanout — FIXED (census PASS max 32): 28 kept go copies; 81 descriptor load groups (<= 12 bits) each on a distinct
  (go copy, kept idle copy) pair; 21 loop-field chunk copy sets {a,p,jl,kl,tl} (oa/ot thirds, cur/base/wrom/xc/xk halves);
  counters' own kept control copies; 22 one-hot split copies replace the binary split shifters; per-group ts/wcs and
  group-index strap copies; 5 wsrc copies. Kept copies verified to survive Yosys (census counts per mapped driver).
4 Depth — rc7 gate depth NK 525 ps / 15 levels; new logic is AND-OR one-hot shifts and 16-bit round incrementers
  between rung 0 and rung 1 (gate textbook depth to confirm).
5 Storage — unchanged: ROM/SRAM macros; copies are 1-16 bit registers. Inherited: the ME_EXTRA x delay line (u_xm,
  ~7 x 128 b < 2 kb) is a flop delay line >= 3 deep (item 5 ring/SRAM) — WAIVED-pending, pre-existing in rc1..rc7.
6 Floorplan — unchanged from rc7b (lattice, full-width bands, pins <= 5.2/um, aspect 1.105, macro fill 43 %).
7 Clock — regional roots as rc7b; rc7 cross-clock fails addressed structurally: (a) ck -> ck_tx rung 0 now captures
  raw s2 operands (round + mask after rung 0, in ck_tx), (b) leaf fault pins land on clk before the OR, (c) tap_q ->
  ib/xl/go landing beside the pins.
  io_hold_margin as rc7b.
8 Schedule — static; 0 data cycles; leaf faults observed one edge later (status only); the strap copy adds one
  register stage on a constant strap; reset release unchanged (2 kit stages).
Bench: rtl/test/tb_qwen_a0_rr8.sv (golden rp1 + REGROOT 7 lockstep + 71 random ops incl. 20 KV, random split 7..11,
tile strap 37) PASS; mutants MUT50-55 all KILLED (results/arch/qwen_a0_rc4_1020/bench_rr8/run_*.log, Verilator 5.050).
