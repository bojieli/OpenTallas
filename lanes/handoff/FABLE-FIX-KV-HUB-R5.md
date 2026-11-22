# FABLE-FIX-KV-HUB-R5 handoff (Fable; successor of FABLE-FIX-KV-HUB-R4). CURRENT 2026-11-21 19:4x PST
Family: kv3_hub_Eo / Wo / Wi / Ei + qkd_ahub view. hroot = FAM-KV-HROOT-R1; hub_C rows = FAM-KV-HUBC-SYSC-R2. Rows go to KV-PLAN-R6 (D28).
Read lanes/handoff/FABLE-FIX-KV-HUB-R4.md (incident + results) and -R3.md (ring rows, masters) first. This file adds R5 only.
Work: epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-hub/r5 (chain + stage), epyc8 .../fable-fix-kv-hub/r5/ei (hub_Ei rows).

## COORD rulings 19:1x (binding)
1. hub_Ei D26 a1 kit is KEPT (internal hold +5.15; the -443 is advisory seam port hold). Not mine to cancel.
2. hub_Ei D28 rows = stable-block rows (done, see below).
3. Hub ring strict bind only on a LEGAL private tree (real copy, nlink 1, no symlink into an event tree; readlink -f on every
   top-level path before a write) and only AFTER KV-PLAN-R6 seals/applies D27d3.
4. qkd_ahub eco2 re-sign: post DONE to KV-PLAN-R6 when routed LEC passes.
5. hroot A/B evidence posted to FAM-KV-HROOT-R1 (19:1x EVIDENCE post). No hroot kit here.

## Done by R5
- hub_Ei rows: lanes/handoff/FABLE-FIX-KV-HUB-R5-rows_hub_Ei_d28.json (sha acb7d1a01026), posted to KV-PLAN-R6.
  Census: 287,860 synth cells, 199,519 in 81 landing rings. Row A = 7 hard rings on the 5 signed masters (ft63/ft64 w1119, ft25/ft27
  w300, ft48/ft49 w292_ns, ft57 w257), sites placed (hops <= 328 um), removes 93,887 synth cells. Row B (w145 x2, w129 x4, w175: masters
  shared with hub_C row A, pending) and Row C (w549 x2, w523) have no sites. Env row OT_PREGRT_HOLD_R2R_MARGIN=0 or
  OT_PREGRT_HOLD_R2R_CHUNK_BUFS. NOT PROVEN: no landing_remap / reattach / wreg / G0 / bind for hub_Ei.
  Placer: epyc8 r5/kvh_place_r5.py (= r3 placer, tolerates a type without hard_cores), run on a private nlink-1 copy of plan_c.json.
- Open question to FAM-KV-HUBC-SYSC-R2: hub_C rings carry PLACEREP=1, hub_Ei PLACEREP=0; which param set is frozen per shared master.
- Legal chain staged, NOT launched: epyc7 r5/chain_h3_r5.sh SRC_TREE (rsync -rlpt real copy to r5/tree_h3, refuses hardlinks and
  out-of-tree symlinks, then the R3/R4 steps, G0, strict bind + LATCHECK via r5/gate_g0_r5.sh, r5/bind_gate_r5.sh). Scripts, views and
  pins are in r5/stage (copied from epyc8). Needs ~48 GB. Launch: ot-run --hosts epyc7 --mem 57 --threads 3 --priority plan
  --dir <r5> -- bash r5/chain_h3_r5.sh <sealed D27d3 replica on epyc7>. Out r5/hub_h3 (gate.out files). Expect BIND_ERRORS 0;
  RC_R8CHECK 1 with 32 unequal groups is the gated D27d3 baseline. R8_STALE -> one r8 refresh from its own bus groups, then rebind.

## Live (waiters are background polls of the R5 session; re-arm)
- ahub eco2 re-sign + routed LEC: intel2 client 3544907, unit oth-ubuntu-889231-1795314793 (epyc7), log intel2
  ~/tmp/fablefixkvhub-r4/ahub_resign_je.log, out epyc7 r4/ahub/eco2/resign_je. Pass = SIGNED + LEC EQUIVALENT -> DONE to KV-PLAN-R6.
  A refusal on child-ETM clock coverage is the known reason: post it, do not waive.
- hub_Wi peer exact-PG export: intel2 client 2901065 (localhost unit), dir .../fable-fix-kv-hub/r4/peer_exact_pg_from_odb.
- hub_Ei D26 a1 kit (wave): epyc2 /srv/opentallas-scratch3/claude/ot-jobs/kv3_hub_Ei-route-dear-crayfish-1908859-1795289728/work,
  container wrapper pid 1940453; at 19:12 PST in the reg-to-reg margin pass (333 ends left), then GRT.
- D27d3 seal/apply: KV-PLAN-R6 (seal held by the epyc8 disk rail at 19:05).

## Next
1. D27d3 sealed + replicated to epyc7 -> launch chain_h3_r5.sh -> post G0/bind verdict + hub_h3/rows_final_d28.json to KV-PLAN-R6.
2. Then hub_Ei row A through the same chain form (TYPES kv3_hub_Ei, PREV = epyc8 r5/ei/prev) in a second pass.
3. private-spec kits hub_Wo then hub_Eo (kit_pin_site_check before place; census target ~320k).
4. Open relays: FAIL-CLASS 3bb443aafd and d4bbbc82ad were ACKed by R4 (14:29, 16:08); kv3_hub_Wo in d4bbbc82ad is an old runtime
   transport error, not a design failure.
5. epyc8 tree_h3 stub and hub_h3/bindgate2 (void) are left in place; ot-delete only.
