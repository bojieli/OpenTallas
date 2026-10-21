# hidx_score_col7_b (HBM-IDXSQ8 2026-10-20, DRIVE-HBM; CRITICAL hb_idx_score family: gate PNGs + checklist to the coordinator, no REVIEW/submit)

Top `ot_hidx_score_col` (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_c.sv): one KEY COLUMN of the IDX-SCORE leaf core (8 heads, 4 head-pair
regions), hard child replicated 4x per leaf (ot_hbm_idx_score_leaf_c7) and 32x per quarter. Outline 345.6 x 345.6 um (8 x 43.2; ~43% util) -- fallback geometry gated in parallel.
Structural change: the leaf (leaf_1017 never closed; leaf_c1 CTS rc137 with 189,723 flops on one root, native32 13,574 drivers)
is split top-down (codex c7 source a1791bb1d): leaf = glue + 4 x this column. HBM-IDXSQ8 adds the native32 fix found by the
first col7 synth census (1,544 drivers, max 74): per-head key pin registers key_h + shift-field copies key_h2 / qst2 (q4dot_n
ports a2/b2), bmul u_pn 16 select copies. Cycle-neutral: chunk_rt_c equivalence (V5.050) pos PASS 2,337 checks, seam / swap /
qlate1 mutants FAIL (results/rtl/hbm_idx_static/score_col7_1020/, sources.sha256 = this RTL).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input lands in a kept region pin/head register (q_p, qv_p, key_h/key_h2, hid_pa/pb); outputs from cs_o
  (head 7) and the region online flops; rst_n reaches only the 2 synchroniser flops of each region's ot_rst_relay_l.
2 Reach: PASS -- block <= 345.6 um.
3 Fanout: fixed -- actual-Liberty native32 census on the mapped netlist PASS: 0 drivers > 32, max 32, 319,037 roots (synth-only
  gate 20261020-214424, ot-epyc6); was FAIL 1,544 / max 74.
4 Depth: PASS (c7 stage structure unchanged: fp32 adds LAT 7 native, q4dot QL 5); gate textbook depth to confirm.
5 Storage: PASS -- query store 8 x 560 b + 8 x 512 b shift copy are per-head registers written once a query (not runtime-indexed
  reads); delay lines >= 3 are ot_hdc_delay_rf32 one-hot rings.
6 Floorplan: PASS -- square, on the 43.2 hard-child lattice, no macros, one std-cell band; all 1,213 pins on the N face
  (~4.0/um at 302.4) so the leaf glue band abuts the columns' N faces.
7 Clock: one root (clk) per column (~47k sinks < 110k refuse line), pin-flop spread <= 80 TT/FF to be shown by the --cts gate;
  io_hold_margin 0.03.
8 Schedule: static, no added cycles (equivalence above). Leaf RESET_F32 = 1: +1 boot-release edge (glue), priced.
