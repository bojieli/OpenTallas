FABLE-FLOW-1047 (11-27, delta since 09:10): 5 new candidates; open classes in CLASSES.tsv S81 47 (up 5), HEAD 32 (up 2), QC 43 (up 6), KV 30 (up 1), FLEET 14 (up 4).
The whole rise is registration of the nine FLOW-0910 candidates plus C-LEG405/SRC-NOT-AT-LEAF (QC). Candidates per review: 23, 15, 7, 8, 9, 5.
Read 10:47-11:10 hub clock, read-only: CLASSES.tsv (last written 09:54) against commit 43513d2ac8c, CLASS-TREND (09:00 cut), CLOSURE.tsv, COUNT-DO-NOT-COUNT.tsv, 48 post files changed since 09:10.
Not done: posts read truncated (300-500 characters; COORD and KV-INT-R3 fuller); VIS-REOWN and FLEET-OPS-R skipped; no host sampled; main not checked. Counts in (b) outside "table moves" are post readings.
Count method as before: rows with count above 0 and status not CLOSED, FOLDED or SUPERSEDED.
Format: class | die | evidence | fix | owner lane.

## (a) NEW-CLASS candidates (5; none is in CLASSES.tsv or in a COORD ruling)
1. C-ISTATION-PACKED-DELAY (lane name S81-LPAD-DK-ISTATION-PACKED-C085) | S81 | leaf t27 and t36 fail kit_topology on LIVE c085 ("packed delay does not preserve exact face epoch/data connection"), 2 of 2 types with lpad leafdn_i0; the adopted plan passed PRE, bind and publish gate with types that cannot generate a kit (S81-INT-R3-PROBE 09:53-10:18) | c51ad635da2 on main 10:45; add kit_topology to the publish dry for every type, not one pilot | S81-INT-R3
2. C-REPAIR-BUF-OVER-MACRO | KV | C-FIRM-RESIZE-OVERLAP is mis-specified: the 225-258 um DPL displacement on 19 of 24 pc types is repair_design repeaters placed over hard pc/SRAM macros and legalized out; none of 1,020 upsized FIRM cells is the cause (KV-INT-R3 09:55) | blockage-aware repair or re-key the class and its check | KV-INT-R3
3. P-ECO-WAITER-RACE | QC | prd_mk refused "lacks 5_2_route.odb" because 6_final.spef lands about 5 min after the route DB (QC-R3-LEC 09:51) | fixed on main 42be10674fb; register and close | QC-INT-R3
4. P-RECEIPT-NOT-COMMITTED | KV (tool is shared) | plan_visual_review.py wrote receipts to the hub worktree without committing; run-item reads HEAD, so five probes sat at WAIT-PLAN-VISUAL until a hand commit (KV-INT-R3 10:20) | the tool commits its own receipt | FLEET-OPS-R5
5. P-CLASS-ALIAS-DRIFT | FLEET | one cause now has four names (C-FILL-RULE-STRUCTURAL, C-SPARSE-OUTLINE, C-SPARSE-PIN-HULL, C-SPARSE-PARTITION-FILL); also C-EXT-PHY-VIEW = C-EXT-CONTRACT-MISSING, C-GPL-REGION-DIVERGE and C-FENCE-HARD-HOLE = C-FENCE-GEOM-ILLEGAL, C-SELECTOR-NAME-MISS = C-RELAY-SEAT-KEYMISS, P-PEER-ABI = C-XDIE-ABI-MISMATCH. Cost seen: QC-INT-R3 10:28 asks for a yes/no that COORD gave at 09:25 item 7 under another name | CLASS-TRACK-R2 keeps an alias column; lanes post the table id | CLASS-TRACK-R2

## (b) Classes whose count rose since 09:10
Table moves
1. C-STATION-BIT-SCRAMBLE | S81 | 1 -> 4 types reproduce | OFF/ON place probes running on t1, t3, t4, t33 | S81-INT-R3
2. C-STREET | QC | 12 -> 21 (lane-band calibrated on retained GRT) | flag READY, default off | QC-INT-R3
3. C-TAP-LOAD | S81 | 10 -> 16 after the predicate moved to the real 1500 gate (a99f6d58b18) | relays or local taps per sibling | S81-INT-R3
4. P-FALSE-GREEN | QC | 0 -> 1 | - | QC-INT-R3
Rose in posts, table not moved
5. P-CLEANUP-LIVE-STORE | FLEET | 1 -> 2: elemB_cv 11-15 ECO DB 08567e48 (210 MB) deleted uncopied; the SIGNED filter read the first of two sign-off files. DNC row CLEARED says the counted record is another sha | COORD safety fix live; test on this case still owed | FLEET-OPS-R5
6. P-EVIDENCE-VOLATILE | KV | third loss of qkd_kvs_pcf and qkd_kvs_pcc_h_head_p: tar restage with a 72 h lease and no PROTECTED-DBS entry; live D not affected. QC s8x_btab and s8x_prog missing since 11-25, so not from the 14:44 delete | re-push from rtx-pro with a protected entry | FLEET-OPS-R5 (AUTO-EXPORT has no agent)
7. P-LAUNCH-SETUP-FAIL | FLEET | 15 more SETUP and NOT-RUN deaths in 95 min (36 in the previous 18 h): no --dir, wrong usage, missing script | 3d76ea4f296 landed 10:35; watch the next hour | FLEET-OPS-R5
8. P-DEATH-UNCLASSIFIED | FLEET | 28 of 52 deaths NO-PATTERN, 12 of them gate states (ROW-GATE or COMBINE NOT-READY) | 7697c6b95ab landed 10:31 | FLEET-OPS-R5
9. P-AUTOMERGE-REVOKE-RACE | FLEET | s81-rstreach-pubstale READY claimed a COORD approval that did not exist; 15 auto-merged READYs still unratified | READY lines cite the COORD line | FLEET-OPS-R5
10. P-SIGNED-CANDIDATE-FALSE | S81, QC | fix NOT DONE: the b4e3 prescreen source cannot be found (FLEET-OPS-R5 10:39) | implement the COORD 10:41 rule (rejudge SIGNED and INDEX row by sha and LEC EQ) | FLEET-OPS-R5
11. C-FILL-RULE-STRUCTURAL | QC | 5 -> 6 collector instances at 2-4 % fill; the corridor re-floor does not close it (FTn monitor 257 -> 612 um), Fable REJECT, row withdrawn | occupied-bin fill metric per COORD 09:25 item 7 | CLASS-OWNERS-R3
12. C-DIECLOCK-PHASE-BIND | HEAD | 1 -> 26 types now fail blocking ADV-PHASE-BIND (0 of 66 rows live) since main 1b7e2685f84 | re-derive on the W12f clock tree | HEAD-INT-R3
13. C-FWDCLK-WRONG-TAP | KV | 1 -> 21 (COORD 09:45); repoint row 38bd202a53ed cuts export pins over 405 from 428 to 10; 435 aliases unmeasured | v6ne goal-cts probe | KV-INT-R3
14. C-LAND-REACH | KV | 0 -> 22 types fail placed; row stays OPEN, UNCALIBRATED | calibrate | KV-INT-R3
15. P-COMPOSE-DROP | QC | 0 -> 25 reset-anchor relays dropped on three types | compose emits a drop list; restore | QC-INT-R3
16. P-STALE-TABLE | QC | START-SETTLE is functional: root_settle 64 against bound 1734 | PRE check now FAIL; row rows_start_settle.py | QC-INT-R3
17. P-HOLD-OVERDUE | QC | 28 -> 56 overdue of 56 holds; 0 KIT-WAVE launches for 2,135 min (09:35) | launch after the hc0 probe | QC-INT-R3
18. C-LEG405 and C-RST-RELAY-REACH | KV | kv3_hroot plan-visual BAD: chains 410-432 um, band ft2_i 91 um below the outline; v6ne cland_rstart -1,476 ps over a 2,505 um span; v2n/v6n raw branches 1.1-1.9 mm | 380 um plan-hop cap; hroot rebase DEFERRED 11-28 09:00 | KV-INT-R3
19. C-XTAP-HOLD family | HEAD | CTS-only on W12f: hd_spn_wshim_tx hold -64 ps, hd_st_n3_transit -110.86 ps FF; hd_spn_end AUTO-GEOM FAIL again | pads only after the tile route and parent STA | HEAD-INT-R3
Down: P-ORPHAN-PROCESS 213 -> 85 (131 killed); NO-PROGRESS jobs 2 -> 0; C-TDREPAIR-REGION-MEAN fixed (b03b2f8ff58); C-STRAP-REACH and C-CA-FARSTRAP-UNSEEN 0 of 119 groups reproduce on W12f (table still 25 and 3); C-GPL-TD-INFLATION not reproduced on East; C-RESERVED-POCKET only on hd_tile; SEALED-INODE 0 shared inodes on nine hosts; hd_tile 37,218 hold cells explained (2,434 inserted); RENAMED-BEFORE-HINTS confirmed and fixed (2aebefa7327); CLOSURE rows backfilled; owner cells now R3.

## (c) Items with no live owner
1. Classes ruled since 09:22 and not in CLASSES.tsv: C-VIEW-PG-PORT-STALE, P-PG-OPEN-INSERTED-CELLS, P-VISUAL-UNMEASURED-HOLD, C-XDIE-ABI-MISMATCH, P-HOOK-RTL-NET, and the folds C-RESET-SEAM-ORDER, C-STATION-OUTSIDE-OUTLINE, C-SPARSE-OUTLINE, C-GPL-REGION-DIVERGE. Stale rows: C-FWDCLK-WRONG-TAP KV 1, P-COMPOSE-DROP 0, C-DIECLOCK-PHASE-BIND 1, P-ECO-TIMER-MISMATCH still OPEN 3 (ruled closed), C-STRAP-REACH HEAD 25 | CLASS-TRACK-R2 posted once (09:21); table last written 09:54 by KV-INT-R3 | CLASS-TRACK-R2
2. QC-INT-R3 10:28 DECISION-NEEDED on the fill metric | already answered by COORD 09:25 item 7; nobody has said so | COORD one line, then CLASS-OWNERS-R3
3. P-PG-OPEN-INSERTED-CELLS census (DNC HOLD on records rebuilt SIGNED with unpowered cells) | no DNC row or post yet | CLASS-TRACK-R2
4. KV counted-view restore and the ruling on which DB counts for pcc_h_head_p (KV-INT-R3 09:30) | KV lanes cannot reach rtx-pro | COORD, FLEET-OPS-R5
5. TOKEN, ROM-WEIGHTS and Explorer store | last posts 21:20, 03:03 and 00:45; KV says token_qwen "stays with TOKEN/COORD"; ROM jobs still write over quota | COORD
6. CBC-FALLBACK 119 S81 types | hourly post still goes to dead S81-DIE-R3; no row in S81 forms A/B/C | S81-INT-R3
7. Fifteen auto-merged READYs awaiting the default and gate-change pass (COORD 09:47) | no lane named | FLEET-OPS-R5
8. Four owner questions forwarded 09:17 (ckptforensics move, Coll_N PHY view, LL D85 credit, SYS_C L664 contract) | no answer; KV works to depth 32 meanwhile | owner
9. Canary on ddba1015b8b5 needs a reviewer (COORD 10:41); the 38 closures are not visible in FLOW-CANARY posts beyond two lists | FLEET-OPS-R5
10. HBM | parked

Live plans: all four have 0 physical confirmations (QC 13 of 13 overnight probes AUTO-GEOM FAIL). First probes launched since 09:44 on all four dies (S81 leaf and col, HEAD 10 plus East C1d, QC hc0, KV 5 goal-cts); 37 jobs running at 10:22.
DNC: 315 rows, last written 10:41 with the elemB_cv CLEARED note; I read the tail only, not a full diff. Signed count 605 any / 484 current, unchanged.
