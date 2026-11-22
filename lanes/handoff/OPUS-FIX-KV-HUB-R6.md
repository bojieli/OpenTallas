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
