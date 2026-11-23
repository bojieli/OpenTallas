# S81-J9-ASSEMBLY-R6 handoff (Opus; started 11-23 05:49 PST; successor of S81-J6-ASSEMBLY-R5). Read R5 handoff + lanes/handoff/S81-J9-MANIFEST-1123.txt first.
Work dirs: intel2 /srv/opentallas-scratch2/claude/s81-j9-r6 (j8_finish.sh, j8_apply_r6.sh = R5 j8_apply.sh with my lane name), epyc10 /srv/opentallas-scratch2/claude/s81-j9-r6 (overlay, compose).

## J8 switch
- Smokes (Codex units on intel2): s81-j8-other-preflights-0548 (col_h10_r0_p4 t1 DRY-PASS 06:01, slice_station__t18 next) and s81-j8-svc-after-hook-0551 (svc_lo rs t1). Outputs s81-j6-r5/j8_stage_hub/smoke_epyc9_partial + smoke_epyc9_svc_fixed.
- When 3/3 DRY-PASS: `APPLY=1 bash s81-j9-r6/j8_finish.sh` (intel2): combine receipts -> mk_cand_j8 (tools 207d4965a0d8, event 891100ef7748) -> coord lanes/handoff/S81_D8J8_source_candidate_1122.json + S81-D8J8-G0-BASELINE-1123.json -> j8_apply_r6.sh (LBL holds, hold_items restore, t5/iq_C/lepe holds, relay env unset, hold split). Output s81-j6-r5/j8_stage_hub/j8_apply.out.
- fleet-scope-argv-clean-gate-0555: GREEN 41/41 (main 3f1adc84bd0); branch already auto-merged af3f7514266.

## J9 tree (epyc10)
- ot-tree-fork j8_cut_tree -> s81-j6-r5/j9_tree: systemd user unit s81-j9-treefork-0556 (log s81-j6-r5/tmp/j9_treefork.log).
- Overlay sha af3f7514266bda35f4dd80bd5aca158c88c6cedc (origin/main 05:50; per-type define bind fix NOT on main yet). git archive tools/ rtl/ -> s81-j9-r6/overlay_af3f7514266b (unit s81-j9-overlay-0607). Then copy+mv per file into j9_tree, + row 3i u_cf 4 files + ADV-TREE-DRIFT view/porous/flow hits from same sha.

## 06:4x state
- J8: smokes 3/3 DRY-PASS 06:20; intel2 unit s81-j8-finish-0621 (APPLY=1 s81-j9-r6/j8_finish.sh): candidate committed (c0c20d96), LBL +59 holds, publish_apply running (log s81-j6-r5/j8_stage_hub/apply_j8.log, j8_apply.out). Local waiter bt7fx9898.
- J9 TREE DONE: epyc10 s81-j6-r5/j9_tree (fork 914 s) + overlay af3f7514266b (s81-j9-r6/overlay_applied.json) + u_cf 4 files + portfix178 3 carries + asbuilt cb499519b9f8 (+seqhost/iqf/gunit). ADV-TREE-DRIFT LAG 0 MISSING 0 (s81-j9-r6/drift2.txt). Posted to hub 06:20.
- GAP MAP lanes/handoff/S81-J9-GAPMAP.tsv (75 hotspot + 23 relaunch, owner lanes fill). Count mapped/unmapped at 10:30 -> COORD.
- COMPOSER epyc10 s81-j9-r6/compose/{jlib.py,compose.py}: recipe JSON steps ops|delta|tool|skip, old-value check, ledger.json. trial1.json (col r2m delta excl core_pin_lead_ps + NO-LAG lead + slice f65f->1ca3d4bf7df6 + col_ygrow --form ecorr + die_grow --cut0 20900.16) = 0 conflicts, final 997c39644f83 (trial1_out). f65f == 6833 except budgets.relay_mid_re_types.
- Gate template: R5 j8_cut_intake/j8_cut_gate.sh (PRE, G0 both, elab --mem 64, bind --strict --all-gaps, lane_asbuilt_latency, G0 compare). J9: reuse J8 g0 report j8_cut_intake/gate/g0_j8. Reset relays: tools/die_plan/reach_relay_plan.py plan PLAN SIDECAR --out-plan --out-sidecar --report. Reprice: plan_gate_pre.py reprice --plan --baseline-plan --out.

## CODEX notes 2026-11-23 07:46 PST

- J8 891100ef774 applied on six replicas (source 61701f3e485d, bind 395/395, 552 files). E9 two same-byte foreign .fork.json inodes repaired. t18 FAIL on ft6 demand 5.767, held; J9 reviewed revision fcc21829441f demand 0.893, exact composed bind pending. c1x_C t5 and c3x remain held for XGA2. Two reviewed COL diagnostic pilots eligible; detached E8 preflight.

## Codex 08:47 PST

- Wave A pre-tap exact epyc10 `s81-j9-r6/compose/wavea_pretap_0838/ft_hops.json` 520b067a45c9. RANKSEAT NO-LAG, COL H10 reach and ECORR/NE/HOPGAP/UCF-MX, Slice CLAND/XGA2/RC31/34, LEPE RC37 and W2/F2/R1/RS1/N2 with retained depth9, SerDes clock + placements, 24-type SVC C7, MISC10c+BKSEL, FT 84/85. Remaining SVC low t1 DFI ft0 now scoped same-cycle 394f6e1c43aa, replay two fields after TAP. Flow E9 137 types / 8 shards under `tap-grid-r6/dr5kit/wave_a_1123`; its coverage helper revision is being corrected for the actual J9cmp tools.
- Source successor epyc10 `s81-j9-r6/wave_a/tree`. Sealed J8 and original J9 untouched. `wave_a/j8_abi_source_ledger.json` carries 32 original J8 source files, including VP XR 11f382f00e21; N2 preferred c37011a52ce2 and BK preferred 9617ad7537cc. C7 sidecar 4ede387a3d9a; native asbuilt `physical/die_plan/s81/plan_of_record/native_bind/asbuilt_run_wavea.json` 555d3793bb64 adds 56 exact SVC aliases and MISC station scope. E10 `wave_a/elab_0844.otrun.log` strict ELAB rehearsal and `compose/wavea_reset_0840/reset.otrun.log` die relay replan.
- Visual d32246864528 reviewed over 406 partitions and six critical types, review `results/geom_review/s81_j9_wavea_d32246864528_1123.md`. This is plan geometry only. No route approval on the altered kit until its exact placement is reviewed.
