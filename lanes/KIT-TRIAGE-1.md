# KIT-TRIAGE-1 (Claude, started by COORD 11-01 04:2x): type-kit FAIL classes -> class fixes + batch relaunch (all dies)
Worktree intel2:/srv/opentallas-scratch2/claude/wt/kit-triage-1 (sparse tools/), branch claude/kit-triage-1-1101 @e8cbe5f6c70. Scratch intel2:/srv/opentallas-scratch2/claude/kit-triage-1.

- 2026-11-01 04:06 PST CLAIM [KIT-TRIAGE-1] G1..G6 kit FAIL classes per COORD brief + OWNER 11-01 "batches, never one by one".
- 2026-11-01 04:06 PST FINDING [KIT-TRIAGE-1 -> COORD, KIT-WAVE-12] (1) STALE ROWS: of 419 FAIL rows in kit_wave_stages.tsv only ~142 are on CURRENT plan blocks (item_key with the plan-of-record block sha); 277 are superseded blocks/events (S81 213, HEAD 21, KV 20, HBM 3) and can never relaunch as such [CHECKED intel2 kit-triage-1/cur.py on hub kit_wave_state + cached plan probes]. Current-plan FAIL table: kit-triage-1/cur_fail.tsv. (2) G1 = all 84 S81 @gen 'unclassified' rows (event 4b5f73abea9) are 'ValueError: macros have LEF but no timing liberty' (gen.log in hub kit_wave/<item>/a1; the WAIT-DEP rule postdates them) -> on the CURRENT S81 plan 3596181ef72 those types and more are WAIT-DEP noview: 127 of 260 S81 types, children with lef but NO lib in the plan: ot_dsrom_su_hcpost_lane_pr (78 types), ot_s81sl_vs (78), ot_s81sl_vn_b (74), ot_v41_rom_elem_q_qxpq_w10_gb (26), ot_s81dv_xfin (16), ot_s81sl_xrt1 (14), mu72_lnland(_nst) 5, coll_lane_w/e_safe8_ntf 4, xrt3 2, gunit_l0..l5/l1c, bksel_c, bk_g, eng_rr_e 1 each. Several have SIGNED die views with _tt/_ff.lib in physical/ref_tile (hcpost_lane_pr MANIFEST verdict SIGNED; vs, xfin, xrt1, xrt3, coll lanes, gunit_*, bksel_c, bk_g) that the plan entries do not reference. Working the class fix: attach lib where a signed view's LEF matches the plan LEF; the rest = S81 core kits.
- 2026-11-01 04:24 PST HOURLY [KIT-TRIAGE-1] burn-down (current-plan rows, kit-triage-1/cur_fail.tsv; superseded rows in brackets) | group -> FAIL -> fix -> relaunched:
  G1 S81 WAIT-DEP child lib: 127 types (84 stale rows) -> child-lib plan delta (6 libs, 2 provisional ETMs) READY+ASK 04:2x, DIE-S81-47 ships delta -> 104 relaunch automatically on the new block sha | 0 relaunched yet
  G2 masked reasons (classifier): ~37 stale rows -> helper G26 (classify on error lines + reclassify CLI) | running
  G3 contract metadata: S81 15 + KV 2 -> helper G3 | running
  G4 place/preflight: KV 10 PORT_BIND + 9 ORD-2013 + 2 cland, QC 2 GPL + 4 macro_channels (DIE-QC-59 069b9d698c0), LEC NEQ 7 HBM/2 QC/2 HEAD -> helper G4 | running
  G5 post-CTS hold: S81 16 + HBM 2 -> helper G5 (pre-route gate -> routed +10 ps gate) | running
  G6 kit_rtl/gen unclassified: S81 9 kit_rtl + 3 gen, QC 5 per-instance params, KV/HEAD 2 -> helper G26 | running
  G7 geom 'plan geometry/site' (COORD 04:2x, largest): HBM 23 + HEAD 6 + S81 4 + KV 1 current (~105 incl. stale) -> helper G7 (standing fill/empty/partial_face exceptions default-on + re-judge batch; clock_reach per-die tap fix) | running
  Not mine / plan-side noted: KV core-view no recipe 8 (kv3_astk, tp8_pv_join_t x3, qkd_hr_*) + HBM 1 -> DIE-KV-60/DIE-HBM-57.

## 11-01 04:40 PST status
| group | FAIL | class fix | relaunched |
|---|---|---|---|
| G1 S81 gen 'unclassified' (= LEF w/o lib WAIT-DEP) | 84 (all superseded) | plan event claude/kit-triage-1-s81lib-1101@9d4908b832a: 5 child libs, 104/127 noview types unblock | 125 S81 relaunched by KIT-WAVE-12 on kva3; stay WAIT-DEP until the lib event merges |
| G7 geom | 102 | claude/kit-triage-1-g7-1101@a8214309dc0 exceptions default-on + rejudge-geom | 0 (5 current-plan release after merge; ~70 real fails -> owner tap fixes + clock_reach INFO proposal) |
| G2/G6 tool/kit_rtl | ~37 / 17+5 | helper running (QC cb* -> DIE-QC-59C) | - |
| G3 contract | 19 | helper running | - |
| G4 place | ~21+11+10 | helper running | - |
| G5 post-CTS hold | 17-18 | helper running | - |
| infra | stage TSV plan_current column | claude/kit-triage-1-1101@2f67707bcea | n/a |

## 11-01 05:03 PST status
| group | FAIL | class fix | relaunched / release |
|---|---|---|---|
| G1 S81 LEF w/o lib | 84 (superseded) | DIE-S81-47 childlib 61fee51a46f merged (my 9d4908b832a withdrawn) | KIT-WAVE-13 relaunch on new plan |
| G7 geom | 102 | int-1101@f9cb0e099d6 APPROVED: exceptions default-on + clock_reach INFO pre-CTS / leaf_reach<=220 at CTS + rejudge-geom | 8 current-plan release after merge (28 pass total) |
| G2/G6 classifier/kit_rtl | 393 reasons fixed, 106 unclassified -> 0 | int-1101 (reclassify) | 9 S81 slice_station retries; rest to die owners |
| G5 post-CTS hold | 16 S81 (+2 HBM tailx_rest with HBM-CORES-KITS-40) | extend HB4 hook b26a827db45 to S81/KV/QC core-kit gens (helper) | pending |
| G4 place | GPL-0305 first (helper) | pending | - |
| G3 contract | 19 (helper) | pending | - |

## CODEX notes
- 2026-11-01 05:49 PST CODEX took over batch class integration on codex/kits-flow-1101. READY38d476057f9 includes G5 1f49968ef2f (HB4 + contract-relative stop), queue-full1097a215d70, qfill29c50ffc7, spareb4a1de44743; 245 focused checks PASS. G3/G4 prep classes under review; no failed verdict overwritten.
- 2026-11-01 06:01 PST CODEX class batch merged main7913128e3 and DEPLOYED intel2: G3 parent_budget prep estimates signed=False/release_qualified=False; G4 shared GPL-0305 plain fallback + status landing grow; G5 HB4 routed hold repair. Async LEC executes within same admitted container (no unreserved second memory cap); six lifecycle tests and actual delayed-proof smoke pass. Relevant combined targeted suites PASS (245 initial,92 async integration,36 G3/G4/source-follow,63 latest source/selection). HBM ctl/split3 stale-src retry assigned HBM core owner.
- 2026-11-01 06:13 PST CODEX batch actual24 LAUNCH at06:05:32 (5HBM/5QC/5KV/5S81/4HEAD), waveRUNNING41->65. Nine immediate mkdir transportFAIL (5HBM+4HEAD) diagnosed: own standalone service omitted OT_HUB_NAME=intel2, so self-SSH intel2 unresolved; no heavy command ran in9. Normal timer environment correct. Future standalone explicitly sets hub env; DNStransport classifier4d67ed9ad ready. Fifteen remaining items queued/running admission. HEAD ctl_n/e transport-only exporter held gate diagnosed; native-free structural recipe9ef4ee5b5 staged, current-source/prepared-cohort export job queued24GB. G3 oldsource failures are not manually requeued before newsource.
- 2026-11-01 08:04 PST CODEX: Main065deployed onIntel2, includingbound-onlyGEN60b (actualS81 avoided21min unuseddie_top emission), exactFTmasklayer6c, restoredSRAMpackage andcurrent signedparentadapter. Cleanphaseintegration codex/kits-flow-1101@5cbf2d52b pushed:179tests+4subtestsPASS, adoptedrealexit+phasecompletionreceipt retained. NativeSRAMendpointclock model8e3cd856b andHCPLmeanproviderceb1afbaf readywithS81owner; true VE_s/VS/RXsb means remainopen. Explicithold_itemsee46 supportsownerrequestedHG/PC,oldsourceS81G3andQC37blockedtypes; normalmetadata/sourcefixretries mustclearholdswhenownedfixlands. QCcellbatch119/119complete via338b,11real/modelcapfindingsownedA0; no95missing-evidence issueleft.
- 2026-11-01 08:14 PST CODEX PARKED on explicit Claude reset. Handoff: handoff/codex_kits_flow_20261101_park.json; phase integration5cb ready, requiredfdc post-synthguard; wavePLACE WIP5f08 NOTenabled. Liveproofjobs preserved. QCcanonicalconfigpush completed; sourcefailures/holds and latestS81strictPASS recorded for Claude.

## 11-01 08:33 PST resume after 05:44 limit (COORD 08:2x)
| group (current plan) | FAIL | owner | class fix | relaunch |
|---|---|---|---|---|
| geom real fails | 17 (HBM 13, HEAD 4) | DIE-HBM-57 / DIE-HEAD-53 | plan geometry (taps/islands, pin reg) | after owner deltas |
| route post-CTS hold S81 | 15 | KIT-TRIAGE-1/G5 | 1f49968ef2f merged + qfail 6c21736a442 | 16 pending rows (src) -> S81 src bump |
| gen contract parent_budget S81 | 15 | DIE-S81-47 / Codex fix merged | S81 src adoption (helper) | after src bump + hold_items clear |
| LEC not equivalent | 12 (+6 old) | helper LEC | pending | pending rows on fix |
| KV port bind + macro decl | 19 | DIE-KV-60 | plan pins / hard cut | owner |
| mkdir DNS + geom_run 143 | 10 | INFRA | none needed | 10 pending rows (hub e1aa524c974) -> next tick |
Superseded FAIL rows: 284 (not counted). fill/empty exception already default-on; 0 current-plan geom passes to release.
