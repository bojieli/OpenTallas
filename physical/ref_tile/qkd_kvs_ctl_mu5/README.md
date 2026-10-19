# qkd_kvs_ctl_mu5 -- structural successor of qkd_kvs_ctl_mu4_safe (KV/system die MU control tile, kvs14 MU)

Lane KV-GRP-CTL/MU5, branch claude/kv-grp-ctl-1019-ctl.  mu4_safe gate (10-19) failed checklist items 3, 4, 5, 7 (and
6 waived); this kit is the structural redesign, not a tweak.  Parallel clock fallback: qkd_kvs_ctl_mu5b (same RTL and
floorplan, OT_SPINE_TREE_PAD=1).  No REVIEW.json is written here (critical tile: the parent lane reviews the gate PNGs).

## What changed (RTL)
- u_lprg -> `qkd_static_kv_layer_programme_mus` (rtl/qwen_sys/mu_qwen_20261018/, new file; `_mu` untouched):
  stage table 9x36x32 b + GAP table 144x32 b moved to two `ot_sram_1r1w_128x256_m1_r2c2` (u_rowa: P_ctrl..P_quiet;
  u_rowb: P_end, next-gap for 4 users, ==0 / ==1 flags), P = r - 2 precomputed at the boot write (bit write mask, one
  32-b word per write, one edge after the accept as before).  The read is issued on the edge that sets c_load (address =
  the beginning context's new stage) and lands on the c_load edge, where the flop table was read: **0 added cycles**.
  Stage-1 gaps are 4 boot registers.  Every event (9 roots + wait expiry) is a REGISTERED flag computed one edge early
  as a plain equality (c_age == P, c_cnt == 2, loaded ==1 flag); start digest/epoch/position checks compared one edge
  early on the pins (bound_* stable >= 146 edges before configured).
- u_wprg `qkd_kv_native_programme` #(SRAM 1, RCOPIES 3): its 36x5x32 b root table (5,760 runtime-indexed flops, missed
  by the mu3/mu4 audits) -> one SRAM macro, read on the start_p edge, copied on the ld edge as before (0 cycles).
  Defaults SRAM 0 / RCOPIES 1 keep every other view unchanged.
- Reset copies (KEPT, family wires marked `ot_rst_split`, spread by ot_rst_copies.py, max 256 loads/copy):
  u_fanr.rs_q x4 (`qkd_kv_es_fan_root2_b` RCOPIES 4; was 756 loads), u_wprg.reset_pin_n x3 (was 409), u_lprg x4;
  landing rst_n 40 / por_n 16 as mu4.  The `re` key is not used: the attribute selects these families (a `$`-anchored
  regexp in an ORFS make variable is fragile); the default regexp still picks the landing families.
- Tile file `qkd_kvs_tiles_hroot_ff_k_mu.sv`: 3 instance lines (u_fanr, u_lprg, u_wprg).  The generator carries the same
  parameters under OT_KV_MU=1 (tools/qwen_kv_die/kv_static.py, kv_static_die.py _boot_join); `kv_static_die.py --rtl`
  emits exactly these 3 lines (checked), but on this branch it also re-flows unrelated d2d__srx/skw ports (pre-existing
  generator drift), so the 3 lines were applied by hand and the rest of the file is unchanged.

## Benches (fleet ot-epyc6, Verilator 5.050; logs results/rtl/mu_qwen_1018/kv/runs/mu5/)
- lprg lockstep `_mus` vs `_mu` MU1, all outputs every edge: PASS mismatches0, 140 boots, 960k cycles, tokens
  254/274/242/249 (aligned 4-user, single-user arbitrary gaps incl. gap 1/2, chaos with faults codes 0/1/3/4).
  Mutants l_off / l_row / l_gap / l_wx FAIL (mismatches 6e5..8e5).
- wprg lockstep SRAM1/RCOPIES3 vs SRAM0: PASS mismatches0 (787 starts, 490 tokens, 25 fault episodes); w_row FAIL.
- mu4 set rerun on mu5 RTL: lint, writer rows, mu2/mu3 lockstep, MU boot e2e (471-word image through the tile, 4 users,
  2660 event edges equal the compiled list), mu4safe exact PASS; all 15 mutants FAIL as expected.

## SAFE checklist (owner 10-19)
1. Pins PASS (inherited): every pin registered (pin_regs, keep_pin_regs, io flops at pins 4 cols); rst_n/por_n 2-stage
   landing, 40/16 copies.
2. Reach PASS by construction / gate measures: outline 345.6 x 475.2 (mu4 475.2 sq passed at 0.2 um/stage); farthest
   flop-to-flop span through the centre column < 405 um except face-to-face W<->E (345.6 um).
3. Fanout FIXED: internal reset regs replicated (rs_q x4, reset_pin_n x3, lprg x4) and split <= 256 by the synthesis
   pass (check PREOPT OT_RST_COPIES lines); event flags are registered, the remaining wide select (fire_u / owner over
   ~150 metadata bits) is one mux level after registered 4-bit flags.  Gate high_fanout list is the witness.
4. Depth FIXED: the 17-level subtract/compare/priority/mux stage is gone (registered flags + plain 32-b equality one
   edge early); worst remaining cones (start check -> e_begin -> SRAM address; flags -> fire_u -> metadata) ~10-12 lv.
   Gate logic_depth is the witness.
5. Storage FIXED: 15.2 kb (lprg) + 5.76 kb (wprg) of runtime-indexed flop tables -> 3 SRAM macros.  Remaining state:
   per-context row registers 4 x 322 b (indexed by context id, not a table), shadow 8 x 32 b boot check.
6. Floorplan WAIVED (util) / PASS (rest): 3 macros on the 43.2 lattice (x 129.6; y 129.6 / 216.0 / 302.4) in one centre
   column, R0, halo 5.4, W channel 129.6 um / E channel 121 um beside the macro pin faces; full-width std-cell rows
   between the macros (45 um) and above / below; aspect 1.375.  Util ~15 % (std ~13-15k + macros 11.7k um2): pin-bound
   by W/E 2524 bits each (5.31 pins/um at 475.2 um; >= 421 um needed at 6/um) -> fill_reason.pin_bound in the spec.
7. Clock FIXED / MEASUREMENT PENDING: symmetric centre-fed spine (clock "spine", OT_SPINE_SYM 1, SAFE_BALANCE 1,
   LEAF_N 16, TREE_PAD 0; mu5b TREE_PAD 1) instead of one TritonCTS root (mu4 TT 182.5 / FF 159.0 ps); SRAM clock pins
   are their own leaves (MACRO_LEAF).  io_hold_margin 0.03.  Acceptance: pin-flop spread <= 80 ps TT and FF (--cts gate).
8. Schedule PASS: static; mu5 adds 0 cycles (lockstep equal on every edge); the mu4 deltas (+1 quiet ck before
   enter/leave, +1 ck config/go/group-fault observation) are unchanged and already in lanes/KV-GEN8.md INBOX.

## Gate
`pre_route_gate.py physical/ref_tile/qkd_kvs_ctl_mu5 --remote auto --cts --mem 32`, log/json
/home/ubuntu/scratch/kv-grp-ctl/gate_ctl_mu5.{log,json} (mu5b: gate_ctl_mu5b.*).  Verdict pending.
