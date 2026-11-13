# HARD-S81-SVC-1 handoff (S81 svc family, DIEVIEW-S81 F3, R-CAP-3; Fable lane; COORD) -- started 2026-11-13 06:14 PST

## Scope
- 16 svc items (svc_hi/lo dsdv_svc_rs*, pvso_entry), 242 failed launches, never placed in the wave.
- Brief: (1) flop memory -> generated macro (sim + interface equivalence); (2) R-CAP re-size/split; (3) floorplan in the core-shape
  freeze; (4) private ot-run kit to place + GRT, renders viewed; (5) READY branches (RTL/macro, plan delta), adopted after 11-15 04:00.

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/hard-s81-svc-1, branch claude/hard-s81-svc-1-1113 off origin/main 4a5e3dcf7e (own clone).
- Work dirs: epyc7 /srv/opentallas-scratch2/claude/hard-s81-svc-1/ (v5/plan_A.json = ready12b-A 18c864518844);
  epyc2 /srv/opentallas-scratch2/claude/hard-s81-svc-1/ (kr/ = kit RTL + closure of the 16 types; fitgate/ = private copy of the MEM v2 gate).
- Logs: intel2 ~/tmp/hard_s81_svc_kr_all.log, ~/tmp/hard_s81_svc_fitgate.log.

## Findings (all [CHECKED] by me on 11-13 unless marked)
1. The memory is ALREADY a generated macro since 11-03 (MEM v2, main): attn_staging 8 lanes -> 8 x ot_sram_1r1w_160x265_m1_r0c0,
   land -> 12 x 160x256, pmem -> 4 x 256x256_m1, pvq -> 17 x 32x128 (sram_gen via tools/mem_compiler/build_s81_svc_fit_1103.py; views in
   physical/asap7_memory_macros_v2; gate results/rtl/s81_svc_memory_fit_1103/run.sh; +0 cycles). The plan contents of every svc type
   already place these 45 macros.
2. Why the wave still sees flops: the macro form is applied by a post-bind step (tools/die_plan/s81_svc_memory_closure.py --kit-rtl)
   that was one line of physical/die_plan/s81/kit_wave/kit_rtl.sh (kit_rtl mode "script"). KIT-OPS-1 moved dies.s81.kit_rtl to mode
   "bind" at the ready12b-A switch (11-12 21:46); mode "bind" calls bind.py kit-rtl directly, so the closure is skipped. Evidence:
   kit_wave.json dies.s81.kit_rtl.mode = bind; epyc8 .../items/svc_hi_dsdv_svc_pvso_entry__t1/attempt_9/rtl/*_bound.sv has
   SRAM_MACRO(1'b0) and no memory_closure.json; gen_lint.json memory_bits FAIL (4 x 160x265 + 512x512 + 640x256 + 8x2120).
   hold_items had no svc entry, so the 16 items were still relaunching at 06:2x.
3. The memory was never the wall. R-CAP (cap_estimate.project on plan 18c864518844):
   - form of record (64 attn_hcore + 8 sx_hrow hard cores, rest flat): 4.14-4.18 M mapped cells (CODEX 11-07, quoted) -> place 4.4-4.6 M, 19-20 parts.
   - provider form A / svc v5 (26 boxes hi, 58 lo; parent soft 228,760 hi / 381,961 lo, svc_prov_meas_1109.json): still OVER on the
     1442.88 x 2747.52/2851.2 outline: place 597k (hi rs t1), 802k (hi pvso_entry t1), 822-852k (lo). The outline term dominates
     (16.6-20.6k pins and 174-310 macros x 2.1 mm half perimeter = 350-590k repeaters).
   - so R-CAP needs BOTH: provider hard cores (R-CAP-3 point 3) AND the tile cut along Y into 2-3 partitions (point 2). Even split
     of the hi form A: 2 parts 241k each, 3 parts 148k each.
4. History that the brief did not carry: svc v5 provider plan (S81-SVCRS-3, events 11-09..11-11) was dropped at ready11r (strict bind
   failed: prov_1109 views did not exist). S81-SVCRS-4 then built all 21 provider rows at the exact v5 outlines: 12 SIGNED, 9
   LOCAL_PASS_NEEDS_PARENT; views still on epyc9 /srv/opentallas-scratch2/claude/s81-svcrs-4/prov/run (46 GB; lanes/S81-SVCRS-4-ROWS.tsv).
   ready12b-A kept the svc_lo +77.76 um growth (2851.2) but has no provider box: svc_prov_event_1109.py refuses plan 18c864518844
   ("not the base outline": it expects svc_lo 2773.44). Open design item S81-A1 (staging SRAM -> transposer 2.15-2.89 mm in one cycle,
   SRX relays, +16 cycles per pass) was never built (S81-SVCRS-3 stopped on a limit 11-11 03:39).

## Done
- 06:14 ASK KIT-OPS-1: hold the 16 svc items (queue, on origin).
- Flow fix in the worktree (not yet committed at this line; see State): kit_rtl_post.sh shared by both kit_rtl modes + kit_wave.py
  kit_rtl_post_cmd + test_kit_wave_kit_rtl_post.py.

## State / next (update below)
- 07:0x: commit fe4468028e in the worktree (not pushed yet): kit_rtl_post.sh + kit_wave.py kit_rtl_post_cmd + 6 tests (pass).
- KIT-OPS-1 06:31: the 16 svc items are HELD (hold_items + route_hold_items, SVC-MACRO-1113). Release = me / S81 die owner.
- MEM v2 gate re-run on a private copy (epyc2 fitgate/, inputs sha-equal to the committed list): FIT_PASS 20,000 edges, 5/5 mutants FAIL.
- Closure on TODAY's bound (ready12b-A bind out_main_7073a6b4a5_b, bind.py kit-rtl as the wave runs it): running for all 16 on epyc2
  (kr_all.sh, 4 at a time, about 12 min per type); hi rs t1-t4 APPLIED. kit_rtl_post.sh run on the real closed kit of hi t2: PASS.
- Running: epyc2 genproof.sh svc_hi_dsdv_svc_rs__t1 (gen + GEN_LINT from the closed kit RTL; intel2 ~/tmp/hard_s81_svc_genproof_hi_t1.log).
- NOT done: steps 2-4 of the brief (split, floorplan, place/GRT kit). See the PLAN post for the form decision COORD has to make first.

## RESUMED 2026-11-13 07:27 (COORD: Fable limit reset; I own svc again; read lanes/handoff/SVC-MACRO-2.md HANDBACK 07:26)
- Checked myself after the handback: closure APPLIED 16/16 on the ready12b-A wave bind, 0 kit-rtl failures (intel2 ~/tmp/hard_s81_svc_kr_all.log);
  GEN + GEN_LINT svc_hi_dsdv_svc_rs__t1 PASS, memory_bits PASS (~/tmp/hard_s81_svc_genproof_hi_t1.log); MEM v2 sim gate PASS, 5/5 mutants fail.
- Memory part (brief step 1) = DONE by READY claude/svc-macro-2-1113@3856aafc01 (my fe4468028e on main 24b08535da; on origin). No new macro, no cycle change.
- Codex recover output reviewed by SVC-MACRO-2 and kept as step 1 of the form: epyc7 hard-s81-svc-1/v5/plan_provider_recover.json, status
  PRIVATE_UNGATED, 14 rs types, die geometry unchanged; pvso_entry t1/t2 OPEN (+57.24 um row offset, new landing placement); reset contract not re-solved.
  Branch claude/svc-macro-2-form-1113@ff8154806c (script only). Untracked Codex files still in wt/hard-s81-svc-1 (not mine, left).
- NOT started: RTL band cut (dsdv_svc_rs_c / ot_s81_svc_attn_s), sim + LEC of the cut, plan event, floorplan, private place + GRT kit.
  All gated on the A/B ruling asked 2026-11-13 07:27. No job of mine is running. Hold SVC-MACRO-1113 stays.
- Next for whoever continues: (1) ruling A/B; (2) band wrapper RTL + benches (tb_svc_h8_protocol, tb_svc_srx_attn, svc mem benches) + LEC with
  boundary flops mapped + R-RTL-6 latency rows; (3) plan event = provider-recover + band partitions + pvso_entry + reset contract, R-STREET
  (final on main 5eefdbe2fa) on the band streets; (4) one band part to place + GRT privately, renders viewed; (5) READY after 11-15 04:00.
