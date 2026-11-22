# OPUS-FIX-KV-HUB-R6 handoff (Opus; successor of FABLE-FIX-KV-HUB-R5). CURRENT 2026-11-21 23:4x PST (latest block wins)
Scope: kv3_hub_Eo / Wo / Wi / Ei + their ring hard cores. NOT hub_C rings (KV-RINGMAC-R1), NOT qkd_ahub strap (KV-AHUB-RH1), NOT hroot B (FAM-KV-HROOT-R1).
Read lanes/handoff/FABLE-FIX-KV-HUB-R5.md first (R3/R4/R5 history). Rows to KV-PLAN-R6 by 11-22 11:30 (D28 cut 12:00).
Work: epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-hub/r5 (tree_h3 private ot-tree-fork of sealed D27d3, hub_h3 outputs). Client logs intel2 ~/tmp/opusfixkvhub-r6/.

## Done
- Base variant (hub_Eo/Wo/Wi rows) PROVEN on D27d3: plan b2910bca0603 (hub_h3/plans/plan_p4.json), G0 PASS, BIND_ERRORS 0, LATCHECK 0, BPC PASS,
  R8CHECK 1 = baseline. ROW posted 23:3x to KV-PLAN-R6: lanes/handoff/OPUS-FIX-KV-HUB-R6-rows_hub_EoWoWi_d28.json (a2249803994d);
  blocks form + full plan in intel2 /srv/opentallas-scratch2/claude/opus-fix-kv-hub-r6/d28/. Base bind_of_record moved to hub_h3/aside/bind_of_record_base.
- Tool fix HARD-RING-WREG-1 (R5 commit) pushed: main ae9a5815f0. Patched into tree_h3 tools/die_plan/clock_landings.py (copy+mv).

## Live
- hub_Ei row A rebind (plan p8 e9be978c3180 = base rows + Ei 7 rings): epyc8 unit oth-ubuntu-136931-1795331754, intel2 client 3293902,
  log intel2 ~/tmp/opusfixkvhub-r6/ei_rebind.log, out hub_h3/g0gate_ei2 + bindgate_ei2. Pass -> post hub_h3/rows_final_d28_ei.json (c34fc3e27a87) to KV-PLAN-R6.
- hub_Ei D26 a1 wave kit epyc2 (KEPT by COORD, not mine): 683k instances, detail route 30% / 42k violations at 23:3x.

## Next
1. Ei rebind verdict -> Ei rows to KV-PLAN-R6.
2. private-spec kits on tree_h3 (plan p8 if Ei passes, else p4 + aside base bind): hub_Wo, hub_Eo, hub_Ei (census target <=320k).

## 23:3x update (wins)
- COORD: start sign-off kits now, in parallel. Kit tree epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hub-r6/tree_b (fork of tree_h3, plan b2910bca0603, base bind).
- LIVE kits (private-spec, src_manifest off): specs ~/coord/autopilot/private_specs/OPUS-FIX-KV-HUB-R6/qwen_kvsys_kv3_hub_{Wo_1121233022,Eo_1121233034};
  runners intel2 pids 3672200 / 3672201, logs intel2 ~/tmp/opusfixkvhub-r6/kit_*.log; work epyc8 .../KV-D27d3/private/OPUS-FIX-KV-HUB-R6/kv3_hub_{Wo_1121233015,Eo_1121233026}.
- PLAN-GATE-PRE vs D27d3 baseline: PASS for p4 and p8 (hub_h3/pre_p4.log, pre_p8.log).
- epyc2 hub_Ei wave kit unit oth-ubuntu-1907616-1795289726 (container pid 1940453): COORD says cancel via ot-run --cancel if DRT > 10k violations at ~02:30 PST.

## 00:3x update (wins)
- First kits (…_1121233022 / _1121233034) FAILED at 3_3_place_gp: OT_CLAND no mapped ring flops under u_cland_ft0_i / ft10_i.
  Tool fix HARD-RING-BAND-1 on main bdb08607ce (landing_place.tcl skips bands whose ring is a hard_cores param_wrap child).
- LIVE kits on rt bdb08607ce36: specs OPUS-FIX-KV-HUB-R6/qwen_kvsys_kv3_hub_{Wo_1122003254,Eo_1122003303}, intel2 pids 1629056/1633552, logs kit2_*.log.
- hub_Ei rebind: G0 PASS 0 errors (g0gate_ei2), elab 0, strict bind running (bindgate_ei2).
- D28 GEN needs tools >= bdb08607ce (Eo/Wo, also hub_C rings) and >= ae9a5815f0 (hub_Ei). Posted to KV-PLAN-R6.
- Lane clone: epyc8 r5/clone branch opus-r6-hard-ring-band (pushed).

## 00:4x update (wins)
- hub_Ei rebind PASS (G0 0 err, BIND_ERRORS 0, LATCHECK 0, BPC PASS). Ei ROW posted to KV-PLAN-R6: lanes/handoff/OPUS-FIX-KV-HUB-R6-rows_hub_Ei_d28.json
  (c34fc3e27a87); blocks_d28_Ei.json (e49c0bf85d58) + plan_e9be978c3180.json in intel2 opus-fix-kv-hub-r6/d28. ALL D28 hub rows delivered.
- LIVE hub_Ei private kit: tree_h3 (plan e9be978c3180 + its bind), rt bdb08607ce36, spec OPUS-FIX-KV-HUB-R6/qwen_kvsys_kv3_hub_Ei_1122003620,
  intel2 pid 2287276, log kit2_qwen_kvsys_kv3_hub_Ei_1122003620.log. DO NOT reinstall plans in tree_h3 while it runs.
- Open: hub_Ei row B/C masters (PLACEREP=0 w145/w129/w175, w549/w523) -> D29.

## 02:2x update after the 01:4x limit (wins)
- RESUMED posted 02:2x. KV-PLAN-R6 picked up row 3 (plan e9be978c3180) at 00:48 as d28/rows/ROWS_OPUS-FIX-KV-HUB-R6.py.
  Future rows need a receipt line: ROWS-READY <LANE> <sha12 of row script> types=<...>.
- FIX-SYNC-KVHEAD KV-C02 band.hard_core flag row for my 25 rings: NO VETO; D28 as the last row if KV-PLAN-R6 binds it before the seal, else D29.
- epyc2 hub_Ei D26 wave kit died by itself at 01:21 with DRT-0255 (92k violations at 20%). Nothing to cancel.
- Kits: hub_Ei PLACED, chain goal route, in CTS (02:20). hub_Wo / hub_Eo past global place (the fix works), in resize / detail place.
  Waiter bolt9appw: failed stage or first cts/grt/route pass.
- NEXT on GRT: read final 5_1_grt.odb TT setup and FF hold (never 5_global_route.rpt), then route DRC -> signoff chain + routed LEC.

## 02:4x COORD ruling (main 03412153064a): private kits count only if SEALED + EQUIVALENT routed LEC
- My 3 kits are --src-manifest off (rt bdb08607ce36) = PROOFS ONLY. Trees tree_b / tree_h3 are sealable forks (parent manifest fa1d8c9906a3).
- When a proof shows it can close (final 5_1_grt.odb TT >= -42, FF hold >= 0): relaunch that type as a SEALED private-spec on the same tree and plan
  (no --src-manifest off; --rt b15a8a1023ed, which is >= 6d2e187f0d floor and contains my fixes). Waiters: ot-wait --durable.
- After sign-off + EQUIVALENT routed LEC: kit_wave.py private-provenance <private_specs/OPUS-FIX-KV-HUB-R6/dir> --lec <routed lec.json>.
- Never edit tree_b / tree_h3 again (a seal must equal what gen read).

## 02:5x SEALED kits launched (COORD: do not wait for proofs)
- Specs OPUS-FIX-KV-HUB-R6/qwen_kvsys_kv3_hub_{Wo_1122025530,Eo_1122025542,Ei_1122025555}: src-manifest ON, rt b15a8a1023ed, goal finish, gen epyc8.
  Runners intel2 pids 2509488 / 2512829 / 2516970, logs ~/tmp/opusfixkvhub-r6/kit3_*.log.
- Proofs (kit2_*, pids 1629056 / 1633552 / 2287276) keep running. A proof showing its type cannot close (GRT TT < -42 not fixable by ECO,
  or setup < -300) -> cancel the sealed twin's units (ot-run --cancel on the exact units only).
- Sealed sign-off + EQUIVALENT routed LEC -> kit_wave.py private-provenance <spec dir> --lec <lec.json>.
