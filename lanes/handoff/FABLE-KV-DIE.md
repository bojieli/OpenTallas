# FABLE-KV-DIE handoff (Fable die-level lane, KV qwen_kvsys). Updated 2026-11-22 04:45 PST.

Goal: remove the KV die stall with ONE die-level D29 change; hand rows to KV-PLAN-R6; launch sealed private rep kits (top 3 families).
Report: lanes/FABLE-KV-DIE-1122.md. Posts: lanes/posts/FABLE-KV-DIE.md. Client logs intel2 ~/tmp/fablekvdie/.
Work dir epyc8 /srv/opentallas-scratch2/claude/fable-kv-die:
- check/ street_rule check of D27d3; leg1/ leg2/ leg3/ = street_rule legalize DRY runs (private, --no-bins); sr_wrap.py = JSON-safe wrapper.
- repo/ = lane clone (main 58ebc21a50 + RING-LITE-2 patch, NOT pushed yet): clock_landings.py, schema.py, die_plan.schema.json,
  test_landing_ring_lite.py, rtl/test/meso/lite/{tb_lite_csc.sv,run_csc.sh}. Tests: t1/ (bench csc + lite), t2/ (pytest).
- tree_a/ = ot-tree-fork of kw45/src_kv_d28_work_r6 (D28 work tree, tools rt 6d2e187f0d65, plan dry5 fcfa38bdb65b). Gate runs go here.
- tmp/ scripts (ringcount.py, difft.py, patch_lite.py). Local scratch copy of rows: scratchpad kvdie/rows/ROWS_FABLE-KV-DIE-R1.py.

## Findings (posted 04:3x, bb10f4a1d7)
Area is not the stall; per-lane landing rings (1,188 of 2,006 bands <= 16 bits, 1-bit ring = 811 cells / 200 flops, LITE = 88 / 18) and
tiles 3-5 reach lengths across with cores 9-17 um off the edges are. street_rule legalize cannot re-floor pv/hg/hgi automatically.

## D29 rows (scripts epyc8 fable-kv-die/rows/, PLAN_IN PLAN_OUT form; apply in this order)
- R1  ROWS_FABLE-KV-DIE-R1.py: landing_ring_narrow on 44 unsigned types.
- R1b ROWS_FABLE-KV-DIE-R1b.py: landing_ring_lite {max_width 8, monitors 1, status_copy true} on 43 types. Needs main >= e08eb28ae039
  (RING-LITE-2, pushed 05:1x; unit tests + bench run_csc.sh pass).
- R5  ROWS_FABLE-KV-DIE-R5.py (COORD 04:5x hg central channel): 7 hg types, head e4/e5 + astk g_ex strips +43.2 um y via core_place
  --seed --no-search, then ft3 station banks rebuilt compact in the new street (y 561.6-602.1). RUDY H overflow v1p2 571k -> 239k,
  v3 516k -> 181k. env FKD_TREE / FKD_RT. Needs landing_remap + clksite_pinclear after it. kv3_hg (ft2, other corridor) NOT covered: open.
- R2 band re-site at pins (after R1b bind), R3 pv in-tile re-floor, R4 hgi array north: proposals posted to the family lanes.

## State 18:00 PST: ECTL CORE REBUILD (COORD 18:0x: I own it) -- CURRENT
- Cause of +5: D26 -> D27d3 re-spaced hg internal_stations bus:o_ectl_Q_N_rq 3 -> 5 regs and the four bus:i_slg_Q_N_krsp rows 5 -> 8 regs
  (bind rule RESPONSE_LAT = 8 + krq + krs: 26 -> 31; QK = RL + 11). Asked KV-PLAN-R6 18:0x whether D29 can restore the D26 counts (fallback:
  37/26 bind, old views valid, no rebuild). No answer yet.
- Rebuild = new kit lineage through the kit wave core path, 4 sealed private kits, goal route, from tree_b (my fork, now USED: do not delete):
  * tree_b edits: cores/harden/ectlk_q/qkd_ectlk_columns.sv (7 module defaults 42/31 + columns guard) and qkd_ectl3_kiss_st_cols.sv
    (CORE_QK 42 / CORE_RL 31); originals saved epyc8 fable-kv-die/ectl/{columns_37_26.sv,cols_wrap_37_26.sv}.
  * core jsons: fable-kv-die/ectl/mk_corejson.py (KV-KT-E0 path b, copied from epyc9 /srv/opentallas-scratch/claude/kv-kt-e0/ectlk/) ->
    tree_b/results/kv_host_regen_1/rtl/qkd_ectlk_q<k>/qkd_ectlk_q<k>_core.json.
  * private plan tree_b/.../plan_of_record/plan_ectl_noview.json = tree_b plan 7897fd6e9b3c with lef/lib dropped on the 32 ectl_q rows
    (kv_core_wave views then lists the 4 modules).
  * specs: private-spec qwen_kvsys qkd_ectlk_q<k> --kind core --tree tree_b --plan plan_ectl_noview.json --bind-out tree_a/.../bind_of_record
    --allow-bind-stale --goal route; list in intel2 ~/tmp/fablekvdie/ectl_specs.txt (stamps 1122174126 / 174201 / 174212 / 174223).
  * runners: intel2 user units fkd-core-ectl-q0..q3-1122, logs ~/tmp/fablekvdie/core_ectl_q<k>.log; work epyc8
    .../KV-D27d3/private/FABLE-KV-DIE/qkd_ectlk_q<k>_<stamp>. All four in gen at 17:44.
  * KV-KT-E0 (11-18) used extra gen args on these cores: --cts-setup-only --two-mode-grt --hold-ff-margin 10 --plan-inst ectl_q<k>; the wave
    core_kit args are []. If CTS / hold fails, add them as plan keys / spec args, not env. The 11-16 signed lineage also needed a tap-centroid
    CTS hook (KV-Q2-CLK), a 2-pass post-route hold ECO (prd m10) and a strip re-route; expect iteration.
- After each signs: export (AGIdock + rtx-pro standard export), new view dir (e.g. physical/die_plan/qwen_kvsys/kvectl4231_1122/<module>/
  lef + tt/ff lib + signoff.json), hard_cores lef/lib rows on the 8 hg types + the two RTL files as a tree payload, post to KV-PLAN-R6.
- NO hg kit relaunch before the views exist.

## State 17:45 PST after the weekly limit (CURRENT; blocks below are history)
- hg kits kv3_hg_v1p2 / kv3_hg (units fkd-kit-hgv1p2-1122 / fkd-kit-hg-1122) FAILED at gen_lint 08:52: rtl_check
  qkd_ectl3_kiss_st_cols__columns_built_for_other_params. CAUSE (read from files): binds since D27d3 (D27d3 bind_of_record, gate_a1 / gate_b3,
  plan lane rh1 + rh12_rebind) instantiate qkd_ectl3_kiss_st_cols with QK_ISSUE_AGE 42 / RESPONSE_LAT 31; the signed qkd_ectlk_q0..q3 views
  (plan lef/lib physical/die_plan/qwen_kvsys/kvhg1_views_1116/qkd_ectlk_q<k>/, guard CORE_QK 37 / CORE_RL 26 in
  cores/harden/ectlk_q/qkd_ectl3_kiss_st_cols.sv) were built at 37/26 (D26 bound 37/26). ALL 8 hg types (32 partitions) stop at GEN on
  D27d3 and D28 until the 4 quarter cores are rebuilt at 42/31. Do NOT relaunch hg kits before that.
- Rebuild inputs: the 11-16 signed kits (epyc10 fable-fix-kv-pv-ectlk/q<k>_m10_p2) are DELETED on every host; only final views survive
  (rtx-pro ~/signed-export-1114/Qwen_ROM/qkd_ectlk_q0: 6_final.odb/def/spef/v + signoff.json; intel2 kv-ectlk-rl-cores37/q0,q1,q3 = run/
  residue only). So new kits must be generated: cores/harden/ectlk_q_corejson.py -> core.json, gen_core_kit_kv.py --core-json ... --plan ...,
  -G QK_ISSUE_AGE=42 RESPONSE_LAT=31 (KV-ECTLK-RL handoff 11-15 describes the parameter-only rebuild), run_kit_kv.sh route, signoff, then
  CORE_QK/CORE_RL = 42/31 + new view dir + hard_cores lef/lib rows on the 8 hg types. About 128k cells per quarter.
- io_cor_v1 kit (fkd-kit-iocor-1122): placed, CTS done, in GRT since 17:13; auto-geom FAIL is advisory. Durable waiters on grt and route:
  ot-wait --durable --kit <work>/gen/kv3_io_cor_v1 --host epyc8 --stage grt|route. Kit rt contains 36d0a6df8f6: leave alone.
- Gate-D poll (fkd-rearm-gate-d) still active; plan lane rh10 bind had 30 R8_STALE at 17:20; KV-PLAN-R6 resumed 17:25 and is sealing D28.
- Rows in the D28 intake unchanged: R1, R1b, R5, R5c, R6 (dry13 applied all).

## State 08:50 PST (COORD 08:4x: three tasks; this block is current, the 08:40 block below still holds for rows / gates)
- KITS (sealed, --goal route, from tree_a = gate_b3 plan 01eb79c44cd6; gen host epyc8 only because the tree is there; nothing pinned):
  kv3_hg_v1p2  unit fkd-kit-hgv1p2-1122  spec ~/coord/autopilot/private_specs/FABLE-KV-DIE/qwen_kvsys_kv3_hg_v1p2_1122083950  work .../private/FABLE-KV-DIE/kv3_hg_v1p2_1122083937
  kv3_hg       unit fkd-kit-hg-1122      spec .../qwen_kvsys_kv3_hg_1122084006                                             work .../private/FABLE-KV-DIE/kv3_hg_1122083959
  kv3_io_cor_v1 unit fkd-kit-iocor-1122 (goal finish; memory note 11-22 says finish dies on resume: if it stops after route, re-run run-item --goal route)
  logs intel2 ~/tmp/fablekvdie/kit_{hgv1p2,hg,iocor}.log. tree_a has NO R6h reset rows: an hg setup miss on the reset spine there is the known
  -560 class, not R5. Read GRT overflow vs FLOW-CLKGRT-R2 566k / 871k.
- R6 = ROWS_FABLE-KV-DIE-R6.py 034899c832bd (in the D28 intake): kv3_hg_v3 +4 added taps clk_t60..63 from tap_split.py on the composed plan
  97a61b154060: max load 5,347 -> 2,970, over cap 2 -> 0. plan_gate_pre on the composed plan with / without R6: 0 findings both. Order: after R5.
- RE-ARMED GATE: intel2 user unit fkd-rearm-gate-d (script ~/tmp/fablekvdie/rearm_d.sh, log rearm_d.log) polls the newest kv-plan-r6/d28/rh*_bind
  every 5 min; on BIND_ERRORS 0 it runs epyc8 fable-kv-die/gate_d.sh once (fresh fork tree_d of the work tree + PRE + G0 + strict bind + LATCHECK
  + BPC -> gate_d1/gate.sum) and posts one GATE-D line. Stop it with systemctl --user stop fkd-rearm-gate-d if D28 is sealed without it.
- RECLAIM (after the io_cor kit ends, via ot-delete, lane dir is guard-protected until then): epyc8 fable-kv-die/tree_b (51 GB);
  later tree_d (51 GB) and, when all three kits ended, tree_a (51 GB).

## State 08:40 PST (supersedes earlier state blocks)
- ALL FOUR ROWS ARE IN THE D28 COMPOSE: KV-PLAN-R6 dry10 (16 rows) has R1, R1b, R5, R5c APPLIED (intake kv-plan-r6/d28/rows/: R1 9860691ee0da,
  R1b 74bdc3ee5a86, R5 6281f8f48b0a, R5c 6e86608e1250, helper kst_xstreet_v3_fkd.py 095576e60380). Its rehearsal rh8 (plan 97a61b154060) is the
  gate of record: G0 1 error = kv3_pv_v3 landing band (PV lane), bind errors = 60 R8_STALE / R8_UNCOVERED on the PV split (PV lane / plan lane).
  Nothing on my rows; hg findings there: routed_reach 18, station_core 10, tap_sink_cap 2 (hg_v3 clk_t52 5,347 and clk_t36 3,372 > 3000).
- My gates: gate_a1 GREEN (R1+R1b), gate_b3 GREEN (R1+R1b+R5 v2+R5c, plan 01eb79c44cd6, tree_a). gate_c3 / gate_c4 (tree_b, plan lane dry7
  compose) stopped by a foreign kv3_pv_v3 finding; abandoned in favour of rh8.
- Kit: kv3_io_cor_v1 sealed private kit on tree_a (plan 01eb79c44cd6), goal finish. Runner intel2 user unit fkd-kit-iocor-1122, log
  ~/tmp/fablekvdie/kit_iocor.log; work epyc8 .../kit-wave/qwen_kvsys/KV-D27d3/private/FABLE-KV-DIE/kv3_io_cor_v1_1122075221; place since 08:06.
  Durable waiters (re-run the same command to read them): ot-wait --durable --kit <work>/gen/kv3_io_cor_v1 --host epyc8 --stage place | finish.
- tree_a FEEDS THE KIT: never gate on it. tree_b (51 GB) is no longer needed: ot-delete refused it (lane dir protected by the private spec);
  retry after the kit ends. Also deletable then: leg1-3 plans, gate_* aside dirs, r5* trial dirs.
- No private hg / pv kit from me (posted 08:30: hg needs R6h + R5 bound = D28; pv waits on the PV lanes).
- NEXT: (1) read the io_cor_v1 kit (place -> finish; cancel only if measured unable to sign). (2) After D28 applies: first kv3_hg_v1p2 D28 kit GRT
  overflow vs 566k / 871k (FLOW-CLKGRT-R2); hg_v3 taps with TAP-GRID-R5. (3) D29 candidates still open at die level: pv in-tile re-floor (R3),
  hgi array north (R4), band re-site at pins for the lite rings (R2), sys_c place region (HUBC-SYSC-R2), street_rule tool limits
  (event JSON crash line 3073; cannot re-floor pv / hg / hgi). (4) Main: RING-LITE-2 e08eb28ae039 pushed; lane clone epyc8 fable-kv-die/repo.
