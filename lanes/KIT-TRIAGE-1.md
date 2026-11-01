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
