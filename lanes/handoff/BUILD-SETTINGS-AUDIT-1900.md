# BUILD-SETTINGS-AUDIT-1900 (2026-11-20 19:xx PST)

Read-only audit plus small fixes. Nothing launched, cancelled or signalled. Lane clone: intel2 /srv/opentallas-scratch2/claude/lanes/bsa1900.

## Method
- Open rows: kit_wave_state.json items of s81 / s81_head / qwen_compute / qwen_kvsys, class not SUPERSEDED/COUNTED/QUEUE-CANCELLED: 626 rows
  (s81 354, QC 178, KV 81, HEAD 13). The effective env is die_gen_env plus item_env (glob, then exact), with nulls removed, the same as
  kit_wave.item_env. Each row is compared with the spec.json gen_env of its last attempt.
- Kits as they run: the config.mk of 276 open kits from their gen hosts, compared with 407 signed kit config.mk under
  autopilot/closed on intel1/intel2/epyc2/7/8/9/10. Signed copies are deduped per type; the comparison is with the newest signed member of the same family.
  Signed coverage is thin: only 19 of 141 S81 open kits and 44 of 99 QC open kits have a signed sibling; KV and HEAD have none.
- Refusals: ~/coord/autopilot/log.txt 11-19 18:31 .. 11-20 18:31 (log lines 258571-282797).

## Findings, ranked by types affected

1. **die_gen_env OT_PLACE_MAX_FANOUT=64 on all 4 dies overrides the R-FLOW default of 32: 554 open types** (S81 315, QC 178, KV 52, HEAD 9).
   KW-FIX-45 (11-12, coord 67f812e6524) predates R-FLOW (11-13, gen_phys RFLOW place_max_fanout 32, proof kits slice_station__t21,
   kv3_sys_SD_v1, coll_ftc). The die value always wins, so the R-FLOW 32 applies only where item_env sets 32. Signed siblings: KV 3/3 at 32,
   while 15 KV open kits run at 64. S81 slice_station signed at 32 on 18 open types that now run at 64. QC signed at 64.
   This changes a default, so it is a READY row: drop die_gen_env OT_PLACE_MAX_FANOUT on s81 and qwen_kvsys. Keep it on QC, where it matches the signed kits. HEAD is outside
   R-FLOW (OT_RFLOW=0), so HEAD keeps 64.
2. **The structural FF hold stop was re-armed by stale per-item OT_HOLD_STOP_PS: 72 open types.** 53 item_env entries had -200 or -300: 51 KV types, plus
   hd_ctl_n and coll_ftm. They are from KW-FIX-8 / DIE-HEAD-59 (11-04), when these values were a relaxation of the -150 stop. Since R-MINIMAL (11-13) the
   die_gen_env value is -1000000, which never stops. An explicit item value wins in gen_phys:7353, so these kits hard-stopped at post-CTS on r2r hold < -200 ps (hold_gate.tcl:177).
   The OT_HOLD_STRUCTURAL_ADVISORY=1 line that gen writes is read by no tool.
   **FIXED** by removing the 53 keys: coord 4b11d936d8f (kit_wave_edit). Started kits keep their config.mk. To revert, re-add the keys.
   Open follow-up for a READY row: make hold_gate.tcl honour OT_HOLD_STRUCTURAL_ADVISORY, or stop writing the flag.
3. **S81 die_gen_env OT_CBC_REACH_UM=405 on the J5 tree, which was bound at 300: 137 J5 rows launched with 405.** It is a d8i leftover from d19639c2515, and was kept in
   81f6a90048a. The fallback trees d8i/h/g carry their own gen_env 405, so they do not need the die key. The key sets cbc_rules.REACH_UM_PER_HOP in gen and in the estimators,
   which affects the ft seam input cap (313 vs 245 ps) and the reach reports. Measured effect: none of the 206 J5 kit SDCs carries a 313 budget, so the cost today is in reports and the estimator only.
   READY row: drop dies.s81.die_gen_env.OT_CBC_REACH_UM. KV keeps its 405 while D25e3 (bound at 405) is live; **the D26 apply must drop it.**
4. **Per-port and pad variants do not inherit the parent's item_env: 94 open types** (S81 81 col `__pv*`, QC 13 `__pad*` / `__pv*`).
   item_env_entry (kit_wave.py:4455) matches only an exact key or a glob. Every other matcher (item_key_matches :2071, the drift check :2088) treats `<key>__...`
   as a match, so the drift check reports nothing. Keys that are missing: OT_NATIVE_RESET_SCOPE=selected (80 S81), OT_GEN_M8_GRANT=1 (80 S81, 11 QC),
   OT_POROUS_VIEWS=all (36), OT_CLAND_STRIP_DENS / OT_GRT_TRANSITION_MODE (QC 11 / 8), OT_MACRO_MOVES (5), port hold margins (4), and the CONS kit set (QC 3-4).
   Examples: col_h9_r0_p5__t1__pv* (10), col_h9_r0_p3__t1__cl8ce97bcb__pv* (5), sle_ctl__cl503337ff__padE0/E4, sle_st_a_v2__pv*.
   This is a semantic change, so it is a READY row for the S81 and QC owners: either add family globs (`col_h9_r0_p5__t1__pv*`), or make the variant generator copy the parent's
   item_env, as the `__cl` splitter does. A blanket inheritance in item_env_entry could re-add keys that `__cl` children dropped on purpose.
5. **Kits that were generated before today's sparse-exit fixes are still live: 78 placed rows** (S81 71 non-leaf with OT_GPL_SPARSE_OVERFLOW=0.25, HEAD 7 with the
   sparse exit and/or -overflow 0.2). HEAD: hd_ctl, hd_host_n, hd_host_e, hd_host_w, hd_serdes, hd_lep0N, hd_spn. All 78 are past place (ENQUEUED or ROUTE-HELD at geom),
   so flow_regen, which handles unstarted rows only and only on a die_gen_env or src change, never touches them. FABLE data on slice_station shows place WNS -128 ps mean with the exit,
   and hd_serdes -1316 ps.
   READY row: route reviewers should treat these placements as built with the wrong setting, and re-place from 3_2 rather than route. List: bad78 in this lane's notes below.
6. **TAP-LIMIT-INFO and other "(info: not blocking)" lines were read as the failure reason: 8 S81 rows** (for example ot_s81sl_leaf__t7 and ot_s81sl_kv_leaf__t1, 13:57 INFRA @gen).
   **FIXED** on main: the ADMISSION filter now drops those lines, with a test in test_kit_wave_advisory_line.py.
7. **Redundant keys, harmless:** S81 OT_PLACE_MAX_TRANSITION=320 (the same default exists on every die); HEAD OT_GPL_HPWL_RATIO=0 and OT_RFLOW=0 (the code already excludes HEAD).
   Dropping the redundant HEAD OT_GPL_HPWL_RATIO through kit_wave_edit would also make flow_regen rebuild the unstarted current-event HEAD rows on the fixed tools.
8. **Pattern scan of tools/:** no further die-name prefix matches on the kit build path. gen_phys `_is_col_type` (col_ prefix) is S81-only by naming. die_top_lint's
   `startswith('s81')` covers the S81 ROM die family (s81_layer, s81_head) on purpose, and is a lint tool, not part of the build.
9. **Not settings problems (design or plan facts):** QC OT_TAP_MAX_SINKS 1000 vs signed 1200 on 31 types comes from the plan clock.tap_max_sinks. S81 PLACE_DENSITY 0.25
   on 74 open kits comes from item_env OT_CONS_UTIL=0.25 (CONS kits), while the signed slice_station kits used 0.5 (10 types differ). OT_GRT_ALLOW_CONGESTION is die-wide on QC/KV,
   and the signed KV and QC kits used it too.

## Launch-blocking refusals in the last 24 h that come from settings or tools (types blocked)
| class | types | still blocking | source / fix |
|---|---|---|---|
| Gen reset identity, captured 405 vs default 300 | 151 (s81 79, QC 47, KV 25) | ~9 | fixed by ecd0239bd5 / 9172a65b43. Still held: kv3_pv, kv3_pv_v7, kv3_pv_v8, kv3_hg_v1, leaf t12, t59, t74, dsdv_slice_lepw_mus_LP__t2. Owners unblock |
| die_gen_env OT_SIGNED_VIEW_SHA outside the die src | 100 (s81) | 0 (last 02:58) | the re-pin left the d8h path. READY: the re-pin tool should rewrite die_gen_env paths |
| SRC_MANIFEST drift (lane writes into snapshots) | 85 (s81 28, QC 57) | ~10 dormant | write into snapshots only through an overlay apply |
| no gen host holds tree d8i (host receipt) | 26 | 0 | the receipt cache refuses hardlinked files (nlink 2). Fixed by adding epyc7 |
| ot-run "no host qualifies" (--dir on root fs) | 18 (QC) | 0 | job dirs on scratch |
| kit_rtl bind names pruned bindcopy_kv_d25e | 15 (KV) | 0 | rekeyed to d25e3 |
| REBALANCE / TAP-LIMIT-INFO read as the gen failure | 12 + 8 | 0 | TAP-LIMIT-INFO fixed in this lane. REBALANCE is already filtered on main |
| HEAD ot_sram_* "type held or not staged" | 8 (HEAD) | 8 dormant | staging list |
Deliberate holds, not counted as tool problems: WAIT-VISUAL 162 (143 still waiting), WAIT-FORM 8, COORD/Fable SKIP-HELD 31.

## Pushed
- main c88d681578: kit_wave info-line filter + test.
- main ec49365989: PROVEN_FIXES rows f2e64e5d3b + 3098d89a95 + test.
- coord 4b11d936d8f: 53 stale item_env OT_HOLD_STOP_PS removed.

## bad78 (die item event): placed with the pre-fix sparse exit
```
s81_head hd_ctl head_rp21z20NF15f_r11b
s81_head hd_host_n head_rp21z20NF15f_r11b
s81_head hd_lep0N head_rp21z20NF15f_r8b
s81_head hd_serdes head_rp21z20NF15f_r11b
s81_head hd_spn head_rp21z20NF15f_r8b
s81 col_h10_r0_p4__t1__pv5b623e07 224567138ab
s81 col_h10_r1__t1__cl95b37463__pv86f5e3b9 224567138ab
s81 col_h10_r2__t1__cl1f5d6c2a__pv0c1de895 3fa87b84b18
s81 col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0 224567138ab
s81 col_h10_r2__t1__cl8b686b3e 224567138ab
s81 col_h9_r0_p2__t1__cl9f71e63d__pva4376595 b05c98f7919
s81 col_h9_r0_p6__t1__pv0012ba28 224567138ab
s81 col_h9_r1__t1__cl49d7a23e__pv047ea3b3 465cb9fe2d3
s81 col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3 465cb9fe2d3
s81 col_h9_r1__t1__cl49d7a23e__pv11dcdcd2 465cb9fe2d3
s81 col_h9_r1__t1__cl49d7a23e__pv4bd36c74 465cb9fe2d3
s81 col_h9_r2__t1__clce45cab5__pv14626557 465cb9fe2d3
s81 col_h9_r2__t1__clce45cab5__pv2833ee2b 465cb9fe2d3
s81 dsdv_slice_iq_C__t1 224567138ab
s81 dsdv_slice_lepe_mu_LP__t2 224567138ab
s81 eng__t1 224567138ab
s81 phy__t1 465cb9fe2d3
s81 slice_station__t27 224567138ab
s81 slice_station__t43 224567138ab
s81 col_h10_r0_p4__t1__pvcc166a6d 224567138ab
s81 col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0 3fa87b84b18
s81 col_h10_r2__t1__cl1f5d6c2a__pvf1512c16 3fa87b84b18
s81 col_h10_r2__t1__cl99efd374__pv4c1f67ff 3fa87b84b18
s81 col_h9_r0_p5__t1__pveda1ecc9 224567138ab
s81 col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4 465cb9fe2d3
s81 col_h9_r2__t1__clce45cab5__pv06a1adf6 465cb9fe2d3
s81 dsdv_slice_c1x_C__t9 3fa87b84b18
s81 ot_s81sl_kv_leaf__t3 465cb9fe2d3
s81 slice_station__t24__cleece78ec 224567138ab
s81 col_h10_r1__t1__cld01bb4ae 224567138ab
s81 col_h10_r2__t1__clac068e56 224567138ab
s81 col_h9_r2__t1__clb8d86cd5__pv6a2b031b 465cb9fe2d3
s81 dsdv_slice_c1x_C__t1 3fa87b84b18
s81 dsdv_slice_c1x_C__t6 3fa87b84b18
s81 ot_s81sl_kv_leaf__t5 b05c98f7919
s81 slice_station__t18 b05c98f7919
s81 slice_station__t27 b05c98f7919
s81 slice_station__t36 b05c98f7919
s81 slice_station__t37 b05c98f7919
s81 slice_station__t43 b05c98f7919
s81 slice_station__t49 b05c98f7919
s81_head hd_host_e head_rp21z20NF15f_r11b
s81_head hd_host_w head_rp21z20NF15f_r11
s81 dsdv_slice_kv512_C__t1 224567138ab
s81 dsdv_slice_lepw_mu_LP__t2 224567138ab
s81 gunit__t1 224567138ab
s81 ot_s81sl_kv_leaf__t5 224567138ab
s81 seqhost__t1 224567138ab
s81 slice_station__t18 224567138ab
s81 slice_station__t36 224567138ab
s81 slice_station__t6__cl0755c26e 224567138ab
s81 col_h10_r0_p4__t1__pvcc166a6d b05c98f7919
s81 col_h10_r2__t1__cl1f5d6c2a__pv0c1de895 b05c98f7919
s81 col_h9_r0_p1__t1__pv697f40c9 224567138ab
s81 col_h9_r0_p2__t1__cl9f71e63d__pv2744f675 224567138ab
s81 col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff b05c98f7919
s81 col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8 b05c98f7919
s81 col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898 b05c98f7919
s81 col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a b05c98f7919
s81 col_h9_r1__t1__cl49d7a23e__pva2370bfd b05c98f7919
s81 col_h9_r2__t1__cl774acf45__pv11b6518d b05c98f7919
s81 col_h9_r2__t1__cl87f3ff59 465cb9fe2d3
s81 col_h9_r2__t1__clc9ad8f7e__pv45d0c698 b05c98f7919
s81 col_h9_r2__t1__clce45cab5__pv09b9967e 465cb9fe2d3
s81 dsdv_slice_lepe_nh_mus_LP__t1 224567138ab
s81 iqf__t1 224567138ab
s81 slice_station__t29__clc7772371 224567138ab
s81 slice_station__t37 224567138ab
s81 slice_station__t40__cl1ea9de02 b05c98f7919
s81 slice_station__t41 224567138ab
s81 slice_station__t49 224567138ab
s81 slice_station__t51 224567138ab
s81 slice_station__t52 224567138ab
```

## COORD add-on: kits running a dly_spread older than f2e64e5d3b
Scan of the kit-dir hooks of 292 live rows (191 ENQUEUED, 101 ROUTE-HELD). 28 live kits carry a pre-f2e64e5d3b dly_spread.tcl, and none of them has the 3098d89a95 slew default: QC 17 and KV 11. All 28 are already placed (ROUTE-HELD), apart from 4 QC rows that are ENQUEUED on the old N46C event, so their placements were made with the old step. S81 and HEAD kits do not use dly_spread. 244 live kits have a gp_noconverge_gate.tcl without the 3098d89a95 320 ps default; those kits are safe only where config.mk sets OT_PLACE_MAX_TRANSITION. Tools pins: the trees of all 4 dies lack both commits (s81 j5tree main_sha 3c913dbdfb23, HEAD 385f61b5582a, QC eb1e73448bd0, KV a2fb7e625dd8). rt/current (803803f530) has both. Ledger rows dly-repair-f2e64e5d3b and place-slew-hook-3098d89a95 were added to tools/autopilot/PROVEN_FIXES.tsv, with a test.
```
qwen_compute cbf_q00_s2 s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbn_q00__cl622f65d2 s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbn_q00__cld7bf7197 s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbn_q11__cl49ae4555 s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbn_q11__cl5cc92dfe s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbx_q10__cl89936551_h s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbx_q10__cl89936551 s29q103S4Q9N46R4A4 ROUTE-HELD epyc2
qwen_compute cbf_q00__cl1b5a6458 s29q103S4Q9N46R4A4 ROUTE-HELD epyc7
qwen_compute cbn_q01__cld9ff4c40 s29q103S4Q9N46C ENQUEUED epyc7
qwen_compute cbx_q10__cl94a12200 s29q103S4Q9N46R4A4 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v1 KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v2n KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v2 KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v3n KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v3 KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v4n KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v4 KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v5n KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v5 KV-D25e3 ROUTE-HELD epyc7
qwen_kvsys kv3_pv_v7 KV-D25e3 ROUTE-HELD epyc7
qwen_compute cbf_q01_s2 s29q103S4Q9N46R4A4 ROUTE-HELD epyc9
qwen_compute cbn_q00__cldbcda913 s29q103S4Q9N46R4A4 ROUTE-HELD epyc9
qwen_compute cbx_q10__cl94a12200_h s29q103S4Q9N46C ENQUEUED epyc9
qwen_compute cbf_q01 s29q103S4Q9N46R4A4 ROUTE-HELD intel1
qwen_compute cbf_q11 s29q103S4Q9N46C ENQUEUED intel1
qwen_compute cbn_q00__cldbcda913 s29q103S4Q9N46C ENQUEUED intel1
qwen_compute cbn_q01__cld9ff4c40 s29q103S4Q9N46R4A4 ROUTE-HELD intel1
qwen_kvsys kv3_pv_v1n KV-D25e3 ROUTE-HELD intel1
```

## COORD rulings, implemented 19:5x-20:5x
1. Fan-out: die_gen_env OT_PLACE_MAX_FANOUT=64 dropped on s81 and qwen_kvsys (coord cbeb0ec1ddd). New gens get the R-FLOW default of 32. flow_regen restarts only unstarted current-event rows.
2. S81 reach: OT_CBC_REACH_UM=405 dropped in cbeb0ec1ddd (19:54:29) and **restored in ac8a92de46c (20:5x)**, following the COORD condition. Reset-identity refusals during the watch hour: 0. But `reset_tree.ResetError ... exceeds reach` recurred 12 times on post-drop attempts (20:00-20:55): leaf t28, serdes t1/t2/t4/t14 x2/t15, svc_lo rs t2/t5/t6, dsdv_slice_c1x_C t6, col_h9_r0_p6 pv0012ba28. This error also failed 6 times before the drop with 405 set (t28 a1-a6 from 19:23), so the drop is probably not its cause. RESET-RELAY-GEN-R3 should root-cause it (legal-site change suspected). KV keeps 405; KV-PLAN-R2 was told to drop it in the D26 apply (post b607b1dd428).
3. Variant inheritance: 28 family globs `<parent>__pv*` / `__pad*` added (19 S81 col, 9 QC) in cbeb0ec1ddd. Exact keys still win. Drift check now uses the item_env_entry rule (main a4fc295c2a, env_key_applies + test).
4. 78 stale sparse-exit rows: **not applied.** kit_wave has no config-only way to start a fresh attempt on a ROUTE-HELD or still-routing row: `retry item@N` releases only an ended attempt, and select() skips in-flight rows. Re-placing would need `kit_wave.py cancel-rows`, which cancels live jobs and is outside my rules. 15 of the 19 ROUTE-HELD rows are also under S81-DIE-R4 hold_items ("no route or retry until J6").
   - S81 rows that qualify (57): 19 ROUTE-HELD (WNS -76 to -2341) and 38 ENQUEUED/routing (WNS -55 to -2606).
   - S81 rows left to route (8, WNS >= -42): slice_station t24, t40, t41, t43 x2, t49 x2, t52. One row is unknown: col_h9_r0_p6__t1__pv0012ba28, RUNNING, no kit yet.
   - COORD decision: approve a cancel-rows pass, or add retry + stage_resume_off once each attempt ends. Per-row data: intel2 /tmp/bsa_sub/rows2.json. The WNS source is run/logs/asap7/*/base/3_5_place_dp.json detailedplace__timing__setup__ws.
   - HEAD live rows (all 7, for HEAD-PLAN-R15):

     | item | event | status | place WNS (ps) | re-place? |
     |---|---|---|---|---|
     | hd_ctl | r11b | route running | +31.8 | no |
     | hd_host_e | r11b | ENQUEUED, queue FAIL | +43.8 | no |
     | hd_host_n | r11b | ENQUEUED, queue FAIL | -16.9 | no |
     | hd_host_w | r11 | route running | -40.2 | no |
     | hd_lep0N | r8b | route running | -412.0 | yes |
     | hd_serdes | r11b | ROUTE-HELD (WAIT-FORM) | -878.3 | yes |
     | hd_spn | r8b | route running | +9.6 | no |
