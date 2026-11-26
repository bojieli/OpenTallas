# FABLE-FLOW-1247 class-mapped flow review, delta since 10:47 (2026-11-26 12:47-12:58 PST, read-only)

Baseline: FABLE-FLOW-1047 plus lanes/CLASSES.tsv as of 11:40 (125 rows, 68 class ids; 110 rows / 53 ids at 10:47).
Sources: CLASSES.tsv diff against the 10:19 copy, CLOSURE.tsv (12:47), LIVE-LANES.tsv (12:07), 49 posts changed since 10:47, autopilot LOOP-GAPS / HUB-SYNC-FAILED / kit_wave.json, RELEASE_TREE count line, origin/main ancestry on intel2.
Not done: rtx-pro could not be reached (name does not resolve from intel2 or localhost), so its free space is unverified; failure_breakdown.py not re-run; post bodies read truncated (about 400 characters per entry); FABLE-INDEP has no new entries since 10:17; ten quiet classes from FLOW-1047 C5 were not re-searched; HBM not reviewed.

Line format: class | die | evidence | fix | owner lane.

## A. NEW-CLASS candidates since 10:47 (not in CLASSES.tsv)

1. C-CLKSITE-LANDPIN (renamed from the kv3_phy_v1 C-GRT-GUIDE-GAP item) | KV, HEAD | a die clock-site cluster blocks the M6/M7 row of cland landing pins; census: KV 29 types / 93 rows, HEAD 6 types / 73 rows, S81 0, QC 0 (KV-INT-R2 12:01) | clksite_pinclear 8 um landing-pin corridor, main 3c51d672cf2; kv3_phy_v1 landpin2 form e332a220fad4 plan-visual GOOD | KV-INT-R2 class lane; HEAD rows have no owner post
2. C-RRL265-WEST | HEAD | hd_lep0N_w reset relay legs 248 um; hook re-derived, legs 124 / 124 / 98 um on replay (12:40) | branch claude/head-west-rrl265-1126 @1fa6d790ef41, default off, merge request open | HEAD-INT-R2; waits on COORD
3. C-BANK-PILE | QC | SU_C p3 96ed559c5f90: bank collapse leaves 43 bins over 0.7 (QC-INT-R2 11:59) | re-spread the bank; candidate withdrawn from 21:00 | QC-INT-R2-SUC
4. C-PV1N-SPLIT | KV | type_split of kv3_pv_v1n: about 8k of 16.3k cut-face pins are multicast duplicates, so only 1 of 5 cut lanes carries payload (12:37) | keep the deepest row per bus before the split | KV-INT-R2 class lane (interim)
5. P-PARENT-STA-MODEL | HEAD | HEAD-SERDES-R2 12:29: parent seam numbers for every seam not captured on a forwarded clock were measured on a cell-delay tree without entry-phase or count-align; routed die clock spreads tap arrivals 947 to 7006 ps, so those numbers "may be wrong in either direction". COORD rulings 10:50 and 12:21 rest on them | parent STA accepted only with routed clock RC and entry-phase rows; rulings cite the model used | HEAD-SERDES-R2 (re-run ETA 15:00)
6. P-FLAG-SCHEMA-UNREGISTERED | all | clk_land_clear and ft_core_detour were posted FLAG-READY while missing from the schema; a plan carrying them would fail PRE SCHEMA-UNKNOWN-KEY (CLASS-OWNERS-B 11:29, 11:37; fixed, hence minimum tools eb5eb7471ef4) | FLAG-READY requires one flag-on PRE on a real plan | CLASS-OWNERS-B
7. P-TREE-FORK-BYPASS | HEAD, QC, FLEET | sub-lanes made hardlink tree copies with cp -al / delta-apply --link, removed own scratch with rm -rf, and stopped ot-run waiters by PID, because a 53 GB ot-tree-fork was held on disk ETA (HEAD-INT-R2 11:47 self-report, CLASS-OWNERS-B 11:49 audit) | a light fork mode in ot-tree-fork so the stock path is not the slow one | none (COORD "under investigation")
8. Names to fold, not new: KV-SYSC (286 of 296 endpoints are C-FSTART-HALFCYCLE), C-PIN-PG-ADJ (C-PIN-TRACK-PG), LEC FAIL-OPEN and ROUTED-LEC-NOT-EXPORTED (sub-causes of P-LEC-PROOF-GAP) | CLASS-TRACK

## B. Classes whose count rose (table = CLASSES.tsv now)

1. C-RST-RELAY-REACH | S81, QC, KV | table 0 -> 124 / 82 / 16 with the new spread check; HEAD still 0 | --rst-spread on main a16f6ffe17d6, strict bind moved to enable time; S81 row 1448cdc4b333 ROW-READY | C-RST-RELAY-REACH + S81-RSTREACH
2. C-STRAP-REACH | HEAD | table 5 -> 83 of 119 strap groups reproduce on W10 (31 opposite-face, worst 1589 um), 8 with no seat (HEAD-INT-R2 10:48) | --reach generator on main 65acbdd7577e; rows 5972976694c5 on 25 types queued | HEAD-INT-R2
3. C-CLK-LAND-OBS | KV, HEAD | landing pins added to the class (A1): KV 29 types, HEAD 6 types; no KV row in the table; S81 row still 8 against 105 measured | clk_land_clear S81+HEAD at 21:00; HEAD clkland_r3 444f91090c4a place probe PASS 12:43 | CLASS-OWNERS-B, HEAD-INT-R2, KV-INT-R2
4. C-LEGACY-VIEW-EOL | S81 | table 1 -> 118 items in S81-ITEMS-1126.tsv (col_h9 r1/r2) | porous-view guard on main 34c0a9945796; H10 R2 ECO LEC EQUIVALENT 55072/55072 | S81-COL-EOL
5. C-LEG405 | S81 | table 6 -> 59 items (55 old-plan leaf); live plan leaf t36 has one station chain at 514 um (plan-visual 11:21) | comb plans ROW-READY, base 409ab8eb5be9 | S81-LEG405
6. C-LEG405 | QC | FWLEAF-C9 8 entries on 6 types; SU_C p3 moves more than 400 bits over 405 um (withdrawn); COLLCORE form A regresses tx_s0 to 414-425 um | FWLEAF-C9 d386343d45c1 queued (G0 open); form A2 by 19:30 | QC-INT-R2-FEFW, -SUC, -COLLCORE
7. C-XTAP-HOLD | HEAD | hd_spn post-CTS census 18,896 cross-tap pairs; pair-affinity rows cut short pairs 1802 -> 78 (str 38 -> 0) | rows cb52a6a22d3b on hd_spn, str, n3_turn; hd_spn row must be re-derived after the SPN tap split | HEAD-INT-R2
8. C-XTAP-HOLD | S81 | table 2 -> row covers 144 live col types (core_pin_lead -60 ps), 32 items in S81-ITEMS | row ffcdabb3cbba ROW-READY | S81-XTAP-COHORT
9. C-SITE-IN-MACRO | QC | no QC row; COLLCORE form A puts 430 d5 seats in SRAM halos (REV3 12:33) | form A2 | QC-INT-R2-COLLCORE
10. C-GPL-TD-INFLATION | HEAD, S81 | flag does not close it: West on W11 still +13.1 % area at pass 1 (gate 10 %), deferred to 11-27 09:00; S81 lepw_mus_C with the flag keeps 114,774 TD buffers (+29.5 % at GPL) | COORD: gpl_td on HEAD only after the West RRL265 fix | CLASS-OWNERS-B + HEAD-INT-R2
11. C-FSTART-HALFCYCLE | KV | kv3_sys_c: 286 endpoints under -150 ps, 545 negative in the FSTART rings (12:19) | - | KV-INT-R2/SYSC
12. P-FALSE-GREEN | KV | publish_gate on the live tree d7c233ac returned FAIL after the apply: plan-visual missing on kv3_hg_v1 and PRE RSTREACH on kv3_pv_v2/v6 at 497 / 520 um (11:07); first post-bind FAIL 11:22, PASS 11:36 | apply only on a gate PASS record | KV-INT-R2
13. P-FALSE-GREEN | HEAD | HEAD-INT-R2 12:46 reports 4 seam rows READY for 21:00 while HEAD-SERDES-R2 12:29 put the same rows and all START-EFALL rows on HOLD (A5) | one of the two posts must be withdrawn | COORD
14. P-RUNTIME-MANIFEST | all | live kit tools pins are all older than eb5eb7471ef4: S81 326992cfe785, QC 45bb7d41e172, KV 1f7f9554db19, HEAD 6b1b36481596; S81-INT-R2 plans a bump to "at least 651548f2188b", which does not contain eb5eb7471ef4; KV pc_landing_extra tools 153ea0f8eaeb do not either | every 21:00 candidate tree built on tools >= eb5eb7471ef4 | each INT-R2
15. P-POSTPUBLISH-DISK | FLEET, QC | every row_gate makes a full 60 GB ot-tree-fork: epyc7 fell about 300 GB/h at 11:30 (QC-INT-R2 11:32); epyc10 113 -> 83 GB; epyc9 lane wrote 220 GB in one window; rtx-pro unverified and no post reports it freed | row_gate on a link fork | none (FLEET-OPS-R3 silent)
16. P-HUB-SYNC-DIRTY | FLEET | failing since 09:53 (3 h), now 3 files: KV publish_gate json, PLAN-VISUAL-REVIEW.tsv, SMELL.tsv | - | none
17. P-LEDGER-STALE | all | CLASSES counts not updated for C-CLK-LAND-OBS, C-GPL-TD-INFLATION, C-TAP-REACH, C-RELAY-SEAT, C-STRAP-REACH although the lanes posted rows; 4 C-OVERSIZE rows still open after COORD closed the class; RELEASE_TREE_SUMMARY still shows HEAD W8b and S81 plan_h2_2249; ALLFIX-*.tsv untouched | - | CLASS-TRACK
18. P-DEAD-LANE-ROUTING | FLEET | LIVE-LANES.tsv regenerated 12:07 now marks dead lanes live (QC-C1Q-CUT last post 06:08, FP-S81 07:25, QC-STA-PROBE 08:00, bind-parallel-1126, codex-colls-rx-reach-1126); CBC-RULES still cc four dead lanes; NOPROG 11:30 addressed QC-FWV1-HOLD | live = posted in the last 2 h and has an agent | CLASS-TRACK
19. Unowned items (autopilot OWNERS.tsv) | S81, QC, KV | S81 102 -> 126, QC 6 -> 15, KV 30 -> 54 | - | each INT-R2

Down: P-LAUNCH-SETUP-FAIL 65 -> 45 job deaths in 2 h (no preflight landed); P-SIGNED-UNVERSIONED rows zeroed; P-WATCHDOG-FALSE-POSITIVE closed (16c46e77be9); P-REVOKE-NOT-LEDGERED 0; C-OVERSIZE closed except S81 kv_leaf__t2; C-PARENT-SEAM-HOLD HEAD mesh and Wshim TX holds cleared (forwarded-clock seams, still valid).

## C. No live owner

1. FLEET-OPS-R3 | FLEET | second review with no post and no coord commit; worktree untouched since 09:32; LIVE-LANES last_post empty | rtx-pro disk, ot-run preflight, hub sync, row_gate fork size, lane quota alerts all unowned | restart with a check that it posts within 15 min
2. S81-REGDROP | S81 | worktree created 11:17, no post; C-RST-PINREG-DROPPED and C-SYNTH-REG-DROP root cause still open (inputs handed over by S81-INT-R2 10:59 and LEC-R2 11:12) | - | restart
3. HEAD merge requests | HEAD | claude/head-seamhold-1126 @91d93d8b846 (4 of 5 seam rows need it), claude/head-int-r2-falsegreen @72e74968b2a (default-on gate change), claude/head-west-rrl265-1126 @1fa6d790ef41: none on main, no ruling | - | COORD
4. HEAD seam / START row conflict (B13) | HEAD | - | - | COORD ruling before 19:30
5. C-CLKSITE-LANDPIN HEAD 6 types / 73 rows | HEAD | found by the KV lane; no HEAD post | - | HEAD-INT-R2
6. KV v6 VO extra rank (+1 cycle on L2302) | KV | proposal 10:57 for a COORD ruling; none posted; plan b0baa3dc built, ingress seats for 61 of 128 legs not derived | - | COORD
7. Class owner column | all | 16 rows of C-FT-CROSSES-CORE, C-LAND-REACH, C-RELAY-SEAT, C-OVERSIZE still read "unowned until assigned" although CLASS-OWNERS-B works them | - | CLASS-TRACK
8. S81 items | S81 | S81-ITEMS-1126.tsv has 238 rows: 118 C-LEGACY-VIEW-EOL rows whose sweep owner FP-CONVERGE-S81 is dead, 100 UNOWNED, 9 unanswered GEOM requests; S81-DSDV-C structural row named for 21:00 with no lane | - | S81-INT-R2
9. Silent lanes still marked live | QC, S81 | QC-DRT-ECO-R2 last post 09:31, QC-INT-R2-HCLEC 08:34, S81-XTAP-HOLD 09:00 | - | integrators confirm or retire
10. LEC | all | 5 records NEED-KIT (2 S81, 2 HEAD, 1 HBM) keep an unchecked routed EQUIVALENT; OT_LEC_GOLD_CONSTFOLD and the twin fix are parked | - | LEC-R2
11. Watchdog rules | FLEET | PLATEAU-V2.live still absent; no owner for enabling it | - | FLEET-OPS-R3
12. Process deviations (A7) | FLEET | no lane owns the tool fix | - | FLEET-OPS-R3
13. Not re-checked this round: C-ENC-CONE-DETOUR, C-PIN-FACE-BUNCH, C-RCK-HALFCYCLE-MACRO, C-FWDCLK-WRONG-TAP, P-CHECKER-AXIS-GAP, P-PREGRT-HOLD-CRASH, P-ELAB-REUSE-DRIFT, P-EVIDENCE-VOLATILE, P-PRIVATE-BASE-DIVERGENCE, P-COMPOSE-DROP (no owner post at 10:47). Covered since: C-VIEW-NO-OBS, P-KIT-BIND-PLAN-MISMATCH and three P-FALSE-GREEN checks by S81-GATE-LINT on main 651548f2188b.
14. HBM | parked

## D. Did the 10:47 dispatches land

| action | landed | evidence |
|---|---|---|
| FLEET-OPS-R3 restart (rtx-pro, preflight, hub sync) | no | no post, no commit, worktree untouched since 09:32. rtx-pro free GB: not verifiable (host unreachable), last known 46 GB, no post says it was freed. Preflight: nothing on main. Hub sync: failing since 09:53 |
| S81-INT-R2 09:00 cut post | yes | CUT-0900 RESULT 10:56; applied 12:47 as event da07bac383 (publish_gate PASS, bind 403/403); two CLOSURE rows |
| S81-INT-R2 item table | yes | lanes/S81-ITEMS-1126.tsv, 238 rows, 11:02 |
| Headline count 604 / 482 | partly | 12:05 hourly and RELEASE_TREE read 608 any plan / 482 current. Current fell by 4 (S81 cores 68/72); any-plan stayed 608 because the 4 moved to deferred re-sign (S81 3 -> 7) |
| Revocations ledgered | yes | DNC HOLD rows in COUNT-DO-NOT-COUNT.tsv (638d2fa7f77), CLASS-TRACK 11:34 |
| CLASS-TRACK folds / owner column / redirect | partial | 17 owner cells fixed, 16 still "unowned"; candidates added as 15 new ids rather than folded; map refreshed but now over-inclusive |
| S81-REGDROP | no | worktree only |
| Street flag | yes | main 2f20eb4a11da, 11:01 |
| C-RST-PLACED | yes | on main (commit 11:21) |
| XTAP seam element | yes | main c92c46a6520b, 11:29 |
| rst-spread | yes | main a16f6ffe17d6, 11:50 (strict-bind condition waived) |
| 7 CLASS-OWNERS-B flags | yes | SUMMARY 11:38; eb5eb7471ef4 is on main; two flags needed a schema fix after FLAG-READY |
| LEC fail-closed | yes | 4f98b480223 on main |
| 96 LEC re-runs | started | 70 in place on four hosts + 26 streamed to epyc8; no result post yet |
| Export carries routed LEC + backfill 31 | yes | main e7ad3dbf2a9; 31 backfilled per LEC-R2. New exports still depend on the rtx-pro disk |
| HEAD whole-die START parent | measured, then invalidated | die_sta c8ba298400b5 at 12:20, COORD ruling 12:21, HEAD-SERDES-R2 HOLD 12:29; routed re-run ETA 15:00 |
| QC sub-agent cap 8 | yes | TTCTLM, CB, FWLEAF2, HC0TAP lanes posting |
| KV-INT-R2 items | yes | post-bind PASS 11:36; landpin, hubleg405, ioentry, PV rsp candidates |

## E. Per-die class trend and 21:00 readiness

| die | open rows now | at 10:47 | direction |
|---|---|---|---|
| S81 | 36 | 33 | Up: C-RST-RELAY-REACH 0 -> 124, C-LEGACY-VIEW-EOL 118 items, unowned 126. 09:00 cut finally applied. |
| HEAD | 22 | 23 | Flat: strap reach measured at 83 groups, 2 forwarded-clock seams closed; all other parent evidence withdrawn. |
| QC | 23 | 18 | Up: +5 rows around sle_hc0; C-RST-RELAY-REACH 82; two of three reviewed candidates came back ISSUES. |
| KV | 18 | 13 | Up: +5 rows; live plan has a failing publish gate; unowned 54. |
| FLEET | 6 | 6 | No change: lane still not started. |

Convergence: 53 -> 68 class ids, plus 7 candidates here. New ids per review: 23, 15, 7.

21:00 cut readiness

| die | live plan | candidates | gates run | tools |
|---|---|---|---|---|
| S81 | da07bac383 (applied 12:47) | LEG405 comb (3 variants), TAPLOAD ce89898649fb, RSTREACH 1448cdc4b333 + sidecar aa76d811d7dd, XTAP lag ffcdabb3cbba, COL-EOL street 7f0946c7b8f1, t23 ops (cut0900A 409ab8eb5be9), DSDV-C | scoped PRE + scoped strict per row only; rows sit on base 409ab8eb5be9, not on live da07; no combined whole-die gate started | live 326992cfe785; planned bump 651548f2188b is below the minimum. Not ready |
| HEAD | W11 4bd6164aeb1e | tapcopy 014eef27ee80 (review GOOD), strap rows 5972976694c5, XTAP pair rows cb52a6a22d3b, clkland_r3 444f91090c4a (place PASS), SPN b2cd8582212e (ISSUES, adopt not blocked), seam rows b39ca62e14bd, START-EFALL rows (ETA 19:30), N3 Turn 3311c157 | each gated alone (W10 or W11 base, dry gates on a worktree); none combined; seam and START rows on HOLD and need an unmerged branch | dry gates on rt af7000e93a9b, which contains the minimum. Ready for the non-seam rows if the combined gate starts by about 17:00 |
| QC | C9 c9eb8883ad40 | FWLEAF-C9 d386343d45c1 (superset of SUL1), COLLCORE form A2 (due 19:30; form A ISSUES), Coll_s C9d badd78bdf36b, Coll_n 5135384a29c5, hc0 tap split (no physical run), STM P2SEAT, tap_window refresh. Withdrawn: SU_C p3 | FWLEAF G0 still open; no combined form built; whole-die LATCHECK 1922 planned | live pin 45bb7d41e172 is below the minimum. At risk: A2 lands 90 min before the cut |
| KV | 4c5a163e9a21 (post-bind PASS; publish_gate FAIL open) | hubleg405 e91b77b96906 (strict rc0, LAT 2746/2746, plan-visual GOOD, Hroot CTS probe running), ioentry 243d78e6b155, PV rsp 28b55a2259b4 (+1 cycle L2114; LATCHECK needs whole-die), landpin tree, PC +4 286185d0d8f7, v6 VO b0baa3dc (no ruling) | hubleg405 whole-die; the rest scoped; no combined form | live 1f7f9554db19 and PC tools 153ea0f8eaeb are both below the minimum. Ready for hubleg405 alone |
