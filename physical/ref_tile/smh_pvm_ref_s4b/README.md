# smh_pvm_ref_s4b -- PVM (attention PV merge leaf) structural SAFE successor of smh_pvm_ref_s3 (H.STA.BLK.14.3, L2H-SMATT 10-19)
Parallel twins smh_pvm_ref_s4a / smh_pvm_ref_s4b (same RTL). Bind the first to close; cancel the other.
Why (s3 @fc7abb541 gate FAIL, artifacts/hbm-pvm-terminal-source-1019): GRT overflow 508 (stripe through the single N std band +
macro-side contacts), TT reg->macro -418.8 ps (all logic confined to one N band 229-300 while the 64x512 macro's data contacts sit on its
W and E faces 30-180 um away), textbook logical roots fd1 2063 / ev 1587 / AND3 1045 / fd0 1037 / NOR2 851 / word_next 518 loads.
Structural fix:
 RTL SAFE 2 (ot_hbm_sm_pv_merge_s3.sv, opt-in, SAFE 1 unchanged): KEPT same-edge copies -- fd0_k/fd1_k and the turn-state copies
  qb/qf/qklt/qk0/qck/qnk/qn0 one per 16-bit operand slice (32 slices; each copy drives 32 operand-mux bits), the 1,024-bit operand mux
  built per slice from its own copies (the 1045/851/523 decode gates become 32 local decodes), fold_a capture enabled per slice, one
  word_next copy per pub_data bit (16:1 select per bit). Cycle-identical to SAFE 1 (sim-checked every cycle against the reference mux).
 Floorplan: 388.8 x 345.6: macro at x 129.6 / y 86.4 (R180); std bands on all four sides (W 127, E 88, S 84, N 105 um); clock_split_km K=8 regional roots. Codex one_north_band / macro_regions / io_exact hooks dropped: standard placement puts cells beside the faces they serve;
  real row halo MACRO_ROWS_HALO_X 6.48 at the macro faces.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- flow pin regs on every input/output (one capture edge each, as s3); reset 2-stage landing with 16 copies (relay split <=32).
2 Reach: PASS -- pin->flop <= ~300 um; flop->macro contact now band-adjacent (s3: 30-180 um N band detour).
3 Fanout: FIXED -- internal roots replicated as kept copies (<=~32); WAIVED ev / tag_d[14]: they are input-pin captures (the flow pin reg is
  the source; RTL copies would need an ABI or +1-edge change), the resizer buffers them at the start of the cycle.
4 Depth: PASS -- SAFE 1 operand registers + LAT7 adders; per-slice local selects shorten the reg->operand/macro cones.
5 Storage: PASS -- the 32,768-bit stack stays one 64x512 p192 SRAM; fold ring 32 b, entry state small.
6 Floorplan: FIXED -- macro on the 43.2 lattice, std bands at both pin faces + N (s4b all four), continuous rows, fill ~34% / 26% WAIVED
  (macro-bound: 171 x 154 um macro + 9.0k um2 std; the bands must flank both contact faces).
7 Clock: PASS -- s3 spread PASS with one root; s4b adds K=8 regional roots; io_hold_margin 0.03.
8 Schedule: PASS -- 0 added edges vs SAFE 1 (benches exact/tight PASS, MUT1-5 + PUBEARLY FAIL; results/arch/hbm_pvm_s4_1019/bench).
smh_pvm is not a critical prefix: submit after a clean gate.
