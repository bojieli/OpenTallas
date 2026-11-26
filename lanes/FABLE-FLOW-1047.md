# FABLE-FLOW-1047 class-mapped flow review, delta since 08:47 (2026-11-26 10:47-10:58 PST, read-only)

Baseline: FABLE-FLOW-0847 plus lanes/CLASSES.tsv as of 10:19 (110 rows, 53 class ids). Owner check uses lanes/LIVE-LANES.tsv (written 09:15, not updated since).
Sources: CLASSES.tsv, CLASS-MAP/TREND (09:38), CLOSURE.tsv (10:37), LIVE-LANES.tsv, 62 posts changed since 08:47, autopilot LOOP-GAPS / HUB-SYNC-FAILED / OWNERS.tsv, COUNT-REVOKED.tsv, origin/main ancestry on intel2, merge-queue log.
Not done: failure_breakdown.py not re-run (it writes); FABLE-INDEP round-2 bodies read only as class tags and headers (41 entries after 09:38); CLASS-OWNERS-B census numbers read from truncated lines; HBM not reviewed; no host sampled directly except one directory listing on epyc12.

Line format: class | die | evidence | fix | owner lane.

## A. NEW-CLASS candidates since 08:47 (not in CLASSES.tsv)

Design
1. C-SYNTH-REG-DROP | S81 | dsdv_gunit_l5f 0033e091829a NOT-EQ; after constant folding 91 of 10,293 points still differ (LEC-R2 10:43); 8 of 989 exported netlists carry the same f12 tail registers (LEC-R2 10:16) | find the synth step that drops the registers; LEC as blocking sign-off gate | LEC-R2 (census) + S81-INT-R2 (root cause: no post yet)
2. C-STRAP-ISLAND | KV | strap_ca_k host_rst_n M7 column x=1109.92 inside die clock islands on 4 pc types; found by the pre-adopt review, fixed in live 4c5a163e9a21 | static check: strap columns vs clock islands on every die | KV-INT-R2; check to CLASS-OWNERS-B
3. C-PIN-ENTRY-HOLD | KV | raw reset/START pad entry FF hold -82 ps on all 4 IO types (io_cor, io_ft, both _v1), KV-INT-R2/HGI-IOCOR 09:55; delta cfec3dac9da0 not adopted | pin_entry_delay chain in generator; candidate to fold into C-PARENT-SEAM-HOLD | KV-INT-R2
4. C-NEWROOT-TAPOFFSET (lane name PV-NEWROOT-PHASE) | KV | added clock roots lack tap_offset rows: v4 24, v4n 29, v6n 46 not fillable (two phase families); PRE hard-fails TAPOFF-MISSING (10:11) | generator emits offset rows with every added root; donor map for v6n | KV-INT-R2/PV-V6
5. C-PC-PHY-INGRESS | KV | 4 plain-PC types STA-reproduce -1.06 to -1.09 ns ingress; 19 pc_v1 geometry-equal, no STA (09:59) | +4 relay_depth plan 286185d0d8f7; needs latency.pc_landing_extra (main 153ea0f8eaeb) | KV-INT-R2/PC
6. C-RELAY-NEARCORE | KV | relay targets within 2.54 um of cores in 20 of 29 pv types on live 4c5a163e9a21 (v4 283, v3e 300, v12e 234); first posted as C-RELAY-SEAT-CLUSTER then renamed in 2 minutes | fold into C-CLK-LAND-OBS relay class (clk_land_clear with halo) rather than a new id | CLASS-OWNERS-B + KV-INT-R2/PV-V6
7. C-CONE-DEPTH | QC | sle_hc0 cl38badc56 xh0.flt cone depth 12, 443 cells, TT -86.96; split landed main 366319e2e3b as a per-type define | cone-depth lint on sticky-fault cones | QC-INT-R2-HCSETUP
8. C-XTAP-SETUP | QC | sle_hc0 clk_t119 9,172 sinks, 76.8 ps cross-tap skew on setup pairs; BLOCKED 10:26: the taps are CTS-generated nets, not plan taps | author clock.added_taps for the type; same-tap seating | QC-INT-R2-HCSETUP (blocked)
9. C-MACRO-TAP-LEGAL | QC | Coll_s clk_t41 became illegal after two macro moves re-legalised 8 of 41 base taps (COLLX 09:21) | tap legality re-derived at every macro move; fold into P-STALE-TABLE | QC-INT-R2-COLLX
10. GRT-EST-OPTIMISTIC | QC | sle_hc0: GRT estimate +44.6 ps, routed SPEF -85.61 (FABLE-INDEP 09:53) | calibrate GRT estimate vs routed per family | QC-INT-R2
11. RING-LUMP | S81 | slice_station t51 landing-ring lump 97,525 instances, 129 bins over 0.7 (FABLE-INDEP 10:00) | likely folds into C-STREET or C-GPL-TD-INFLATION | S81-INT-R2
12. Names to fold, not new: C-LEG405-HUBEXP (KV) -> C-LEG405; C-PIN-PG-ADJ and C-DRT-METAL-SPACING (QC slw_fe_v1, 204 DRT) -> C-PIN-TRACK-PG QC row; ca-strap-lateral-far (KV kv3_phy 1560 um, 5 tags) -> C-STRAP-REACH KV row; REPAIR-BUF-INFLATION -> C-GPL-TD-INFLATION; TAP-SPAN-SKEW -> C-TAP-REACH; KIT-VIEW-NOT-POROUS -> C-LEGACY-VIEW-EOL | CLASS-TRACK

Process
13. P-POSTBIND-PROOF-DROP | QC | stock post-bind did not forward the West SC rows proof, bind refused ROWS-NO-PROOF (09:30); fixed main 7a5c7eb130 | - | QC-INT-R2-TOOLS (fixed; needs a row to close)
14. P-WATCHDOG-FALSE-POSITIVE | QC, S81 | PLATEAU rule R3 "silent log = DEAD" marked kits at 1 and 9 violations CANCEL-ELIGIBLE (QC-DRT-ECO-R2 09:23); PLATEAU-V2.live still absent | R3 needs a violation floor; calibrate before enabling v2 | no live owner (PLATEAU rules belonged to FLEET-OPS-R2)
15. P-GRT-RESTART-LOOP | S81 | col_h9_r1: one chain ended rc 143 after 11 h of GRT and 5 kits restarted GRT from 4_cts (FABLE-INDEP 09:58) | no automatic stage restart without a changed input | S81-INT-R2 (kits now cancelled 10:44)
16. P-REVOKE-NOT-LEDGERED | S81 | see B20; proposed as a member of P-LEDGER-STALE, listed here because it changes the count

## B. Classes whose count rose (table = CLASSES.tsv now)

1. C-CLK-LAND-OBS | S81 | table 8 -> 105 types by ADV-CLK-LAND-OBS (CLASS-OWNERS-B 10:05; relay-in-core folded in); 443 relay sites cannot be cleared within 120 um, 364 of them on one point in ot_s81sl_kv_leaf__t5 | clk_land_clear flag (main a2c8c178f54a) at 21:00; t5 needs a floorplan item | CLASS-OWNERS-B; t5 to S81-INT-R2
2. C-RST-RELAY-REACH | S81 | table 0 on all four dies; S81-RSTREACH 09:58 on 409ab8eb5be9: 15 types with 22 raw hops over 300 um (kv_leaf t2 2231 um), 22 types with reset refs over 405 um | construct merged bde3792c3bb; rows per type | C-RST-RELAY-REACH + S81-RSTREACH (table not updated)
3. C-LEG405 | QC | table 0 -> 4 fw types with first hop 1390-1411 um (FEFW 10:33), SU-L1 delta on 7 types, STM p2l 540-700 um | b1402a4c0ef2 (SUL1) and FEFW rows at 21:00 | QC-INT-R2-SUL1, -FEFW, -HCSETUP
4. C-LEG405 | HEAD | table 0 -> 3 types: hd_spn/hd_spn_end be_i hop 433 um, n3_turn FT hop 544/500 um | SPN plan b2cd8582212e (LEG405 0 in gate); n3_turn station | HEAD-INT-R2
5. C-LEG405 | KV | table 2 -> 3 hub-class (sys_SD_v1 cland_up 407.7) plus 423 PV export pins in 19 types and kv3_phy cland_up 431.5 that the HUB agent marked "not mine" | export relay tool on main 2998032f4e4, plan 02e3a7e851d5 | KV-INT-R2/HUB; PV and phy pins unowned (C8)
6. C-LEG405 | S81 | 28 round-2 review tags on old-plan families (most frequent class); real under-staged legs stay 6 | comb plans 45a24fe57a99 / 3ff656023621 ROW-READY | S81-LEG405
7. C-GPL-TD-INFLATION | S81 | table 3 -> at least 10: dsdv_slice_*_C family, 7 placed members BAD on resize buffers (FABLE-INDEP 10:05), 18 tags | gpl_td flag, three place-only probes in flight on epyc7 (10:31) | CLASS-OWNERS-B
8. C-LEGACY-VIEW-EOL | S81 | table 1 -> COL H9 R1/R2, 34 kits checked, 16 tags; root cause corrected at 10:05 (not the legacy LEF) | porous qbank view in the kit build + preflight check | S81-COL-EOL (started 10:45, no result)
9. C-PARENT-SEAM-HOLD | S81 | table 2 -> 3: slice_station__t26 otherwise signed, boundary hold -36.01 ps on 148 endpoints | parent arrival measurement | HEAD-SERDES-R2 (asked 10:39)
10. C-PARENT-SEAM-HOLD | HEAD | measured 10:49: mesh<->serdes PASS +14.6 ps, Wshim TX PASS; host_n FAIL 4 of 60; NEW host_w -> st_k5 ring control -50.53 / -48.04 / -41.25 ps; C18 A2 and START-HOSTN still unmeasured. Net 5 -> 4 open with one new member | ROW-READY SEAMHOLD-HB4-HOSTN-RST, SEAMHOLD-CTL-K5-DI; whole-die parent for START | HEAD-SERDES-R2
11. C-TAP-REACH | QC | table 1 -> 30 of 116 types flagged by PRE TAPREACH, 2 over 1.5x radius; cA4 clk_t3 confirmed at 74.5 ps skew | taps clk_t20/t21 in COLLCORE v3 form | QC-INT-R2-COLLCORE; generator CLASS-OWNERS-B
12. P-STALE-TABLE | QC | table 4 -> about 60 types with tap_window/tap-set mismatch (STALETABLE, main cb5b3ce62a) | tap_window refresh in the 21:00 form | QC-INT-R2-TOOLS
13. C-TAP-LOAD | QC | +1: sle_hc0 clk_t119 9,172 sinks | see A8 | QC-INT-R2-HCSETUP (blocked)
14. C-PIN-TRACK-PG | QC | no QC row; slw_fe_v1 cldb4efe33 204 DRT (161 metal spacing) and the cl7479 case | fe/fw family lane | QC-INT-R2-FEFW
15. C-STRAP-REACH | KV | no KV row; kv3_phy strap legs about 1560 um (routed clean in that block) | all-four-group reseat | KV-INT-R2
16. C-XTAP-HOLD | HEAD | table 6, disputed: class lane reproduces 1 of 20 kits; new CTS data: host_w FF hold t4 -55.84, n3_turn FF hold -121 at u_rst_in | taps per band not implemented; seam element branch 1bb6be5205e6 not merged | C-XTAP-HOLD + HEAD-INT-R2
17. P-FALSE-GREEN | KV | 0 -> 1: plan applied 10:19 with "no PASS record" from publish_gate (advisory) and post-bind skipped | apply requires the gate record | KV-INT-R2
18. P-FALSE-GREEN | HEAD, S81, QC | HEAD +1: W11 gate summary says FAIL on the MONLEG KeyError crash and is waived by hand; S81 +1: auto_geom PASS-COND vs FAIL (sent to S81-GATE-LINT, no post); QC +1: 08:57 cut post said post-bind was running when run 1 had refused | crashed check = FAIL; fix the MONLEG check | each INT-R2
19. P-RUNTIME-MANIFEST | QC, KV, FLEET | QC: C9 inherited the C1q tools pin, post-bind needed 3 runs; KV: cut tree tools predate pc_landing_extra; FLEET: runtime sync FAILED 10:20, recovered 10:49 (rt/current 06d9aad55a24); test_schema_file_in_sync failed twice | cut script refreshes tools pin | none (FLEET-OPS-R3 silent)
20. P-LEDGER-STALE | all | table 8, new members: the 4 revoked records (dsfd_node_LLd/LLfd/LLfu, dsdv_gunit_l5f) are still SIGNED in autopilot/OWNERS.tsv at 10:47, COUNT-REVOKED.tsv last written 01:31, hourly count still 608/486 at 10:05; S81 09:00 cut has no result post and no CLOSURE row; ALLFIX-*.tsv untouched since 11-25; RELEASE_TREE_SUMMARY 10:38 still shows HEAD W8b; LIVE-LANES frozen at 09:15; CLASSES rows for C-CLK-LAND-OBS and C-RST-RELAY-REACH not updated | revocation writes COUNT-REVOKED in the same step as the ruling | CLASS-TRACK; S81-INT-R2 for the cut row
21. P-POSTPUBLISH-DISK | FLEET | rtx-pro root 99 %, 46 GB free under the 90 GB reserve: every rtx-pull since 11-25 22:30 is DISK HOLD, 53 units pending, so nothing new can be counted on any die (KV-INT-R2 10:28); intel1 80 -> 46 GB (a KV delta-apply wrote a real 53 GB copy); epyc10 299 -> 113 GB; epyc9 lane wrote 188 GB in one window. epyc2 and epyc7 recovered to 272 / 273 GB | free 45 GB on rtx-pro or rule on the reserve; delta-apply refuses a non-hardlink target | none (addressed to dead FLEET-OPS-R2)
22. P-LAUNCH-SETUP-FAIL | all | table 17 (3 h) -> 65 job deaths in 2 h across 17 lanes: CLASS-OWNERS-B 13, QC-INT-R2-SUC 12 (permission denied, read-only FS), head-int-r2 7, S81-ALLFIX-INT 6, KV-INT-R2 5 | ot-run dry preflight | none (FLEET-OPS-R3 silent)
23. P-HUB-SYNC-DIRTY | FLEET | cleared 09:44, failed again 09:53 and still failing 10:48: lanes/HEAD-SERDES-R2-ROWS.tsv, lanes/PLAN-VISUAL-REVIEW.tsv uncommitted in the hub checkout | hub sync commits lane TSVs | none
24. P-DEAD-LANE-ROUTING | FLEET | redirect works for SMELL-WATCH and most VIS-REOWN; still dead-lane only: PLATEAU-ACT 10:00 and 10:31 (S81-C9-ROWS), NOPROG 09:30, CBC-RULES 10:17, VIS-REOWN 10:07 (S81-OWN-DSDV), KV export request to AUTO-EXPORT | those scripts do not go through post_redirect; map needs sub-lanes | CLASS-TRACK
25. P-INPUT-RECEIPT, P-KIT-BIND-PLAN-MISMATCH | S81 | +3 and +1 round-2 tags | - | S81-INT-R2 (no post on either class)

Down or closed: P-ROUTE-NO-VIEW-GATE S81 87 -> 61 stopped, 69 cancelled, 8 resumed CTS-only, 7 kept; P-HOLD-OVERDUE QC 6 -> 0 (55 holds re-owned); P-SIGNED-UNVERSIONED closed (73 rows CREDITED-UNVERSIONED; table still shows 70); C-OVERSIZE S81 4 -> 1, HEAD 1 -> 0 with the flat check; C-FT-CROSSES-CORE flat (272 / 1 / 50 / 78); UNOWNED items QC 20 -> 6, KV 111 -> 30.

## C. No live owner (per LIVE-LANES.tsv)

1. FLEET-OPS-R3 | FLEET | listed live with empty last_post; no post file, no coord commit, only an empty worktree made 09:31 | its 4 classes (P-POSTPUBLISH-DISK, P-RUNTIME-MANIFEST, P-LAUNCH-SETUP-FAIL, P-HUB-SYNC-DIRTY) and the items below are unowned | restart the lane
2. Items waiting on that lane | FLEET | rtx-pro disk hold (B21); KV .building 53 GB dir on intel1 needing an ot-delete; HUB-SYNC-FAILED; lane quota alerts; 30 old epyc9 route-only waits and the ot-run guard draft; review of dccb5961549 (it is on main with no review post) | - | FLEET-OPS-R3 or COORD
3. C-STREET + C-PIN-TRACK-PG flag | all | branch 58d9cbfdb26c is not on main; C-STREET-R2 push dry-runs died 09:25 (rc 6) and 09:31 (rc 2); no C-STREET post since 09:12 | - | CLASS-OWNERS to re-drive; otherwise no street flag at 21:00
4. CLASSES.tsv owner column | all | 17 rows still name a dead lane or UNOWNED: P-FALSE-GREEN (S81, HEAD, QC), P-INPUT-RECEIPT (S81, QC), P-RUNTIME-MANIFEST x5, P-POSTPUBLISH-DISK x4, P-CLOCK-TAPS-COPY (S81, HEAD), P-RESET-RECEIPT | set to the die integrator | CLASS-TRACK
5. Classes with an owner name but no post since 09:40 by anyone except the reviewer and CLASS-TRACK | S81, KV, QC | C-ENC-CONE-DETOUR, C-PIN-FACE-BUNCH, C-RCK-HALFCYCLE-MACRO, C-VIEW-NO-OBS, C-FWDCLK-WRONG-TAP, C-FSTART-HALFCYCLE, P-CHECKER-AXIS-GAP, P-PREGRT-HOLD-CRASH, P-KIT-BIND-PLAN-MISMATCH, P-ELAB-REUSE-DRIFT, P-EVIDENCE-VOLATILE, P-PRIVATE-BASE-DIVERGENCE, P-COMPOSE-DROP | - | CLASS-OWNERS-B for the C- ones (it runs 7 other classes), CLASS-TRACK / INT-R2 for the P- ones
6. C-RST-PINREG-DROPPED and C-SYNTH-REG-DROP root cause | S81 | COORD 09:23 and 10:14 asked S81-INT-R2 for the flow step; only LEC-R2 has posted | - | new S81 sub-lane (S81-SYNTH-DROP)
7. S81 plan items | S81 | UNOWNED 97 -> 102; no S81 item table (KV has KV-ITEMS-1126.tsv); CBC-FALLBACK 119 col_h9 types; GEOM-REQ-UNANSWERED up to 17 h; sub-lanes S81-GATE-LINT and S81-COL-EOL named but without results | - | S81-INT-R2
8. KV export pins | KV | 423 PV pins in 19 types and kv3_phy cland_up over 405 um, declined by the HUB agent; 4 unclassified triage rows; v6 VO 109 bits "needs architecture decision" | - | KV-INT-R2/PV-STRUCT; VO is an owner question
9. QC queued items | QC | tt_ctlm, cbf/cbn/cbx FIX x6, sle_st_a_v1 STA-PROBE, C-XTAP-HOLD cb rows: "lanes start as slots free" (6 sub-agent cap); QC-INT-R2-HCLEC last post 08:34, HC0 LEC r2 verdict not posted | - | QC-INT-R2
10. HEAD whole-die parent | HEAD | C18 A2 1746 START rows and START-HOSTN need the START tree in a whole-die parent; no lane builds it | - | HEAD-SERDES-R2 next, or a HEAD-DIECLOCK-R2
11. Watchdog rules | FLEET | PLATEAU R3 defect (A14) and PLATEAU-V2 enable have no owner | - | FLEET-OPS-R3
12. Dead lanes whose integrator is COORD in the map | all | ABSTRACT-EXACT, LEC-AUTOFILL, VIS-REOWN, AUTO-EXPORT still receive requests (FABLE-INDEP 09:53, KV 10:23) | map them to LEC-R2 / a live export lane | CLASS-TRACK
13. Map gaps | all | about 25 posting sub-lanes are not in LIVE-LANES.tsv (S81-RSTREACH, S81-LEG405, S81-SVC-T5, S81-TAPLOAD, S81-T23-COHORT, S81-COL-EOL, QC-INT-R2-SUC/SUL1/TOOLS/COLLX/HCSETUP/HCHOLD/STA/FEFW, RESIGN-R2, C-OPPFACE-CA, six KV class agents); HEAD-INT-R2 shows an empty last_post | regenerate the map each hour from posts | CLASS-TRACK
14. HBM | 112 UNOWNED | parked, no action

## D. Did the 08:47 dispatches land

| lane / action | landed | evidence |
|---|---|---|
| S81-INT-R2 die items | partial | route gate applied (09:49: 61 stopped, 5 cancelled; 10:44: 64 cancelled, 8 CTS-only, 7 kept); LEG405, TAPLOAD, RSTREACH, T23-COHORT sub-lanes posted rows. Missing: 09:00 cut result and CLOSURE row, item table, root cause for the two revocation classes |
| HEAD-INT-R2 die items | yes | W11 4bd6164aeb1e adopted 10:35 with clean scopes only; class results 09:56-10:23; OWNER-OVERRIDES.tsv 10:16 |
| QC-INT-R2 die items | yes | ASSIGN 09:10, 55 holds re-owned, C9 post-bind PASS 09:47, tools on main cb5b3ce62a / 7a5c7eb130 |
| KV-INT-R2 die items | yes | KV-ITEMS-1126.tsv (155 rows) 09:10; G6+v6R3+pcstrap 4c5a163e9a21 applied 10:19 |
| CLASS-OWNERS: C-RST-RELAY-REACH sub-lane | yes | START 09:04, merged bde3792c3bb 09:27; CLASSES rows still 0 |
| CLASS-OWNERS: C-PIN-TRACK-PG | partial | rows added; code sits in the unmerged street branch |
| Merge c-leg405-stage-seats | yes | 5632156a860 is an ancestor of origin/main |
| Merge c-tap-load-r2 | yes | main c0f4b9382a8 (post 09:29) |
| Merge c-xtap-hold-census | yes | main 9e32a0d35ef6 (post 09:26) |
| Merge c-rst-relay-reach-r2 | yes | main bde3792c3bb |
| Merge c-street-pg-sizing-r2 | no | 58d9cbfdb26c not on main; two push dry-runs died |
| Merge fleet-ops-r2-preflight-reservation | yes, condition unmet | dccb5961549 on main; no FLEET-OPS-R3 review post |
| Merge head-west-271-parent-share | yes, condition not verified | 3868c7c8b31f on main; no post showing the re-run tests |
| CLASS-OWNERS-B | yes | 7 classes with checks or flags on main (a2c8c178f54a, 15aa96420647, c1eb47a150c3, 9d4ceaf16f83), GPL-TD probes running; C-GPL-TD convergence not proven |
| FLEET-OPS-R3 | no | no post, no commit |
| HEAD-SERDES-R2 | yes | first measured parent seam hold 10:49 |
| QC-DRT-ECO-R2 | yes | census 09:23, ECO-HANDOFF.live 09:30; silent since 09:31 (waiting for DRT end) |
| RESIGN-R2 | yes | 73 rows CREDITED-UNVERSIONED, signoff.py stamps flow_tag (main 8b5c8097a365); 55 records have no fleet DB and were accepted as legacy |
| CLASS-TRACK rows + LIVE-LANES + redirect | partial | 110 rows, FIX-LANDED.tsv, map written; redirect misses PLATEAU-ACT, NOPROG, CBC-RULES; map frozen 09:15 |
| LEC-R2 | yes | hc3 d5fde EQUIVALENT 172097/172097; gunit_l5f and dsfd findings; twin fix parked |
| FABLE-INDEP | yes | 68 entries since 08:47, 0 GOOD in round 1; round 2 has GOOD verdicts on at least slice_station t26, kv3_phy and kv3_sys_SD_v1 |
| Route gate on s81c8 units | yes | S81-INT-R2 09:49 and 10:44 |
| HUB-SYNC cleared | yes, then regressed | OK 09:44, FAILED again since 09:53 |
| Revoke 4 records | ruling only | not in COUNT-REVOKED.tsv or OWNERS.tsv; count unchanged |
| P-SIGNED-UNVERSIONED closed | yes | OWNERS states show CREDITED-UNVERSIONED; CLASSES rows not zeroed |

09:00 cuts, final: QC adopted 08:57 (post-bind PASS 09:47); KV applied 10:19; HEAD applied 10:35; S81 no adoption and no result post.

## E. Per-die class trend

| die | open class rows now (C- / P-) | at 08:47 (existing + candidates) | direction |
|---|---|---|---|
| S81 | 33 (20 / 13) | 10 + 17 | Up. Counts rose in C-CLK-LAND-OBS, C-RST-RELAY-REACH, C-GPL-TD-INFLATION, C-LEGACY-VIEW-EOL; 3 new candidates; no cut adopted. Down: old-plan route units gated, C-OVERSIZE 4 -> 1. |
| HEAD | 23 (13 / 10) | 10 + 18 | Turning. W11 adopted; parent seam measured (2 of 5 closed, 1 new); C-STRAP-REACH cleared on n3_turn; C-LEG405 and C-XTAP-HOLD still open and the table undercounts LEG405. |
| QC | 18 (7 / 11) | 8 + 11 | Mixed. C9 adopted and bound; holds re-owned; screening counts jumped (TAP-REACH 30, STALE-TABLE 60) because checks now exist; 4 new candidates around sle_hc0. |
| KV | 13 (10 / 3) | 4 + 4 | Up in classes (5 new candidates from six class agents), down in unowned items (111 -> 30); plan applied; two GOOD kits cannot count because of the rtx-pro disk hold. |
| FLEET | 6 (0 / 6) | 2 + 4 | Worse. rtx-pro blocks all counting, job deaths 65 in 2 h, hub sync failing again, and the lane created for it has not started. |

Convergence test: 11 classes at 21:00, 34 at 08:47 (11 + 23), 53 ids in the table now, plus 11 new design and 4 new process candidates in this delta. About half of the new names fold into existing classes (A12). The signed count is unchanged at 608 / 486 and should fall by 4 once the revocations are ledgered.
