FABLE-FLOW-1447 (11-27, delta since 12:47): 2 new candidates; open classes in CLASSES.tsv S81 56 (up 6), HEAD 36 (up 4), QC 46 (up 3), KV 35 (up 1), FLEET 18 (up 2).
The rise is the 1247 flow and deep-review registrations (commits 30df6f20ab20, db2692be5f5c, f548b533676a); the table was last written 14:14. Candidates per review: 23, 15, 7, 8, 9, 5, 2, 2.
21:00 check: S81 on track; KV on track with two open blockers; HEAD has a gated form, but a thin one that passes only with a typed deferral; QC is the die at risk of having no gated form.
Read 14:47-15:15 hub clock, read-only: CLASSES.tsv with aliases against c0e31963dd78, CLASS-TREND 1247-deep and fixedsite-reg rows, the four COORD rulings on ROWS_FABLE-RC-*_1247 (12:55-12:58), CLOSURE.tsv and COUNT-DO-NOT-COUNT.tsv (both unchanged since 12:47), 47 post files.
Not done: the four ROWS_FABLE-RC-*_1247.tsv files were not read row by row, only through the COORD rulings and CLASS-TRACK-R3's 12:59 commit; sub-lane posts read at 185-600 characters, 20 expanded; VIS-REOWN and FLEET-OPS-R skipped; no host sampled; main not checked.
Format: class | die | evidence | fix | owner lane.

## (a) NEW-CLASS candidates (2)
1. C-GPL-POSTTD-TAIL-SPARSE | HEAD | on sparse kits the Nesterov tail after the timing-driven pass spreads free cells into empty strips: hd_lep0N C1d HPWL 12.20M -> 18.65M (+53 %) at 2.27 % movable util; hd_lep0N_w +41 %; the C1d place regressed against r6 (r2r max 983 -> 1,125 um, captures over 405 3,016 -> 3,575) and EAST was dropped from W13 (HEAD-EAST-R4 14:17, 14:43). Not C-GPL-TD-INFLATION (buffer area) and not C-TDREPAIR-REGION-MEAN (trigger) | fix on main 015260988651, default off; class requested at 14:17, not registered | HEAD-INT-R3 (HEAD-EAST-R4)
2. C-DIECLOCK-TRUNK-UNPINNED | HEAD | the one die-clock regen (k4sc, built from scratch) moved the trunk, so 1,198 of 1,389 START remaps are REMAP-SUSPECT with |dTT| up to 1,512 ps; hd_tile k4 and PHASE-BIND left the 21:00 cut and the MANIFEST is now due 11-28 03:00, hard stop 09:00 (HEAD-INT-R3 13:34, 14:21). Same pattern as C-RST-WAVEFRONT-UNPINNED, on the clock: a local change re-solves a die-wide structure | seed the trunk from W12f (the lane's Route B) and make that the default for any regen | HEAD-INT-R3 (HEAD-TILE-R3)

## (b) Classes that rose since 12:47
Table moves from the deep reviews (placed evidence)
1. C-FILL-RULE-STRUCTURAL | HEAD 3 -> 23, QC 5 -> 15, S81 2 -> 7 | outline re-floor row for the 14 QC logic tiles (ruled 12:56); corridor metric only for 5 collectors | INT-R3 lanes
2. C-PIN-REG-REACH | HEAD 16 (new row), QC 3 -> 13, S81 1 -> 5 | HEAD rows ready for part; no stock knob for RELOCATE_OFF_WINDOW | HEAD-INT-R3, QC-INT-R3, S81-INT-R3
3. C-LAND-REACH | KV 0 -> 58 of 58 landing types fail -42 ps at place | re-fit at CTS before sizing the row | KV-INT-R3
4. HEAD placed: C-TAP-REACH 1 -> 15, C-PARENT-SEAM-HOLD 5 -> 14, C-LEG405 6 -> 13, C-RST-RELAY-REACH 0 -> 10, C-STREET 0 -> 9 | none has rows in W13; the static checks under-read (tap model 292 against 916 um at CTS; placed-bin model 201 against 482) | HEAD-INT-R3, CLASS-OWNERS-R3
5. S81: C-ISTATION-PACKED-DELAY 2 -> 9, C-RST-RELAY-REACH 0 -> 5, new rows C-CS-BANK-UNSEATED 4, C-HOLDCHAIN-NET-NOT-DNT 1 (fixed 2645bd5c4a8f), C-STRAP-REACH 2, C-HIFANOUT-SELECT 1 | S81-INT-R3
6. Others: C-FWDCLK-WRONG-TAP QC 72 (new row), C-FIXEDSITE-FIRM-OVERLAP QC 1, C-SEAM-GAP-UNDECLARED QC 1, C-RST-WAVEFRONT-UNPINNED HEAD 1, C-EXT-CONTRACT-MISSING KV 1 -> 2, P-CLASS-ALIAS-DRIFT 7 -> 13, P-WAVE-ALLOWLIST-STALE 1. Down: C-STRAP-REACH HEAD 25 -> 0, C-STREET QC 21 -> 6, C-TAP-REACH KV 32 -> 7, C-LEG405 QC 18 -> 11
Rose in posts, table not moved
7. C-FWDCLK-WRONG-TAP | KV | the repoint row fixes distance but FAILS on phase at CTS on v6ne: export insertion spreads 176 ps; 53 of 69 buses launch from a different tap than their forwarded clock and fall outside the receiver window (up to +651 ps TT); the type STA cannot see it (KV-INT-R3 14:02) | DECISION-NEEDED open; QC's 72-type repoint row has the same exposure, two CTS probes launched 13:02 | KV-INT-R3, QC-INT-R3
8. C-RELAY-SEAT-KEYMISS and P-FALSE-GREEN | KV | back on tonight's base: sys_c kit on core5 fails blocking gen_lint, 13 of 25 relay_sites keys seat nothing; all whole-die gates had passed, and the census had run on D (14:28) | re-key row due 17:00; sys_c held from kit volume | KV-INT-R3
9. C-FENCE-GEOM-ILLEGAL | KV new die row | 8 FENCEGEOM SINGLETON on kv3_hub_Eo with the new blocking PRE (lane name C-FENCE-SINGLETON) | merge the one-cell fences into seats | KV-INT-R3
10. C-TDREPAIR-REGION-MEAN | KV new die row | sys_c: five tiny cluster regions pull the mean overflow to 0.122 while the top region is at 0.729 (13:10); SMELL's "19 passes" is a log-line count, 1 real repair | type-scoped gpl_td (7fe44a3034f3); SMELL counter fix | KV-INT-R3, FLEET-OPS-R5
11. C-RELAY-SEAT-KEYMISS, topology sub-cause | S81 | t27 probe 3: 16 of 78 seat keys still unseated after the rename fixes; the plan models a parallel relay tree, the KIT-RD-1 netlist is a serial chain (S81-INT-R3-PARAM 14:40). COORD names it C-RELAY-CHAIN-TOPOLOGY-MISMATCH; it is not in CLASSES.tsv | register or alias; plan relay_split follows the netlist | S81-INT-R3
12. P-ROW-POSTTAP-REMAP | QC | compose r001 NOT-READY: the fwdclk repoint row and SU_C p9 both rewrite clock.landing_contract on su_c; neither order composes although each row was READY alone | merge the two edits into one row | QC-INT-R3
13. P-COMPOSE-DROP | QC, KV | r002 NOT-READY: emit_drop_list writes paths unescaped, so any path with "[" never matches itself (199 SU_C tap drops unnamed); KV 10,822 drops, all attributed | escape fnmatch in compose_drop_guard | QC-INT-R3, CLASS-OWNERS-R3
14. P-STALE-TABLE | QC | TT probe 2 failed at the fixed-site hook: 63 seats name INVx5, synth maps INVx3 (lane name C-FIXEDSITE-MASTER-STALE); alias it here, not under C-FIXEDSITE-FIRM-OVERLAP | r3c gating; TT DEFERRED 11-28 09:00 | QC-INT-R3
15. P-RESET-RECEIPT and P-FALSE-GREEN | HEAD | the rebind guard accepted a hand-forged evidence set (review 14:29); G0 passed with 1,389 START taps missing; KV start_tap_ports prints required=0 with no WARN | native_cover check on main b0e4ea41494, default off | HEAD-INT-R3, CLASS-OWNERS-R3
16. P-POSTPUBLISH-DISK | FLEET | epyc7 97 %, epyc8 93-99 %, intel1 92 %: full forks per probe (HEAD four 55 GB trees, S81 two 48 GB worktrees); 26 of 63 job deaths since 12:47 are NOT-RUN | writer_watch installed; ctln_dens 55 GB still protected by a private spec | FLEET-OPS-R5
17. C-CONE-DEPTH | KV new die row | sys_c u_dcal.u_seq -177.5 ps at CTS, about 17 levels, in a generator shared with QC | joint row, request to QC at 13:18 unanswered in posts | KV-INT-R3, QC-INT-R3
18. C-XTAP-HOLD family | KV, S81 | v6ne post-CTS setup -1,612 ps, hold -236 ps; S81 t12 CTS classified into three existing classes, no row tonight | rows 11-28 | KV-INT-R3, S81-INT-R3
Down or closed: C-HOLDCHAIN-NET-NOT-DNT fixed; C-EXT-CONTRACT-MISSING KV clock contract fixed from signed records; C-REPAIR-BUF-OVER-MACRO tool on main (97d3f2b13552), proof running; LEC 96-batch 0 NOT-EQ; orphans 87 -> 80; PRE GEOM without baseline reads 0 inherited overlaps on all four plans; C-FIRM-RESIZE-OVERLAP not reproduced on HEAD.

## (c) Items with no live owner
1. COORD has not posted since 12:58 | open: KV 14:02 DECISION-NEEDED (repoint row in or out of the 21:00 form; close C-NEWROOT-TAPOFFSET), HEAD-EAST-R4 14:17 class request, S81-INT-R3-PARAM 14:39 candidate, HEAD's typed deferral of blocking ADV-PHASE-BIND (HEAD-INT-R3 12:59 "object if you want otherwise") | COORD
2. Unregistered since 14:14 | a1, a2, b9-b11, b14; aliases to add: C-FENCE-SINGLETON, C-FIXEDSITE-MASTER-STALE, C-START-TAP-PORT-MISSING, C-AHUB-ETM-CLOCK-CONTRACT, CA-SEAM-B, P-GEOM-INHERITED-MASK, C-RELAY-CHAIN-TOPOLOGY-MISMATCH | CLASS-TRACK-R3
3. S81: 8 kit_rtl failures on live c085 (7 svc_hi types "clk_c0 got 0 bound leaf", kv_leaf t2) | DEFERRED 11-28 09:00 to "S81-SVC / plan core clocks", which is not a live lane; the publish gate now blocks only new-vs-live failures | S81-INT-R3 names a sub-lane
4. FAIL-ROUTE-1115 FAIL-CLASS 8070467972, open 9,039 min | handed to HEAD-EAST-R4, HEAD-CASEAM-R4 and back in 30 min; nobody answered | HEAD-INT-R3
5. PLAN-GATE-PRE WAITER-FAIL 7a0b8797e635 on HEAD-CASEAM-R4 13:58 | the result reads as a pass; raised after the substring fix 02080d86b56 | FLEET-OPS-R5 checks the fix is deployed
6. Open-PG check on the 68 counted S81 cores | due 15:00 from S81-INT-R3-VIEWS; no post yet at 14:47 | S81-INT-R3
7. HEAD sibling rows for 13 + 9 + 15 + 10 placed types (b4) | assigned for the 11-28 09:00 form; TAP-REACH goes to "HEAD-SEAMCA-R3", while the live lane is HEAD-CASEAM-R4 | HEAD-INT-R3
8. SMELL-WATCH still addresses FP-CONVERGE-KV, KV-ALLFIX, KV-OWN-PV-R2, KV-OWN-RSTREACH | FLEET-OPS-R5
9. TOKEN parked on the KV plan regeneration, which has no date | KV-INT-R3
10. Four owner questions from 09:17; HBM parked

## 21:00 forms
- S81 | ON TRACK | D2 020158eb5fe3 and B2 9008e90f6da8 pass G0, PRE, strict bind 403 and LAT 947 on rt ad3c4eeda357 (14:27); D3 (plus XR lo11), D162 and E2 in bind; publish D3 if it passes by about 15:00, else D2. Left: seal, replicate, publish gate. Risk: epyc7 at 97 %.
- KV | ON TRACK, two blockers | base core6t (F-core5 + START-SETTLE, carries the C-XDIE-ABI-MISMATCH OBS1 row) is green on G0, PRE, ELAB, bind, LAT 2746 (13:49). Blockers: b9 FENCEGEOM on hub_Eo under the new tools, and the b7 decision. Rows due 18:00; sys_c kits held after apply (b8).
- HEAD | GATED BUT THIN | W13 no-EAST 4fca0de51ee0 passes the full chain on rt b71c5218e0b5 (13:13) only with 22 MISBOUND entries DEFERRED; bare PRE fails ADV-PHASE-BIND on 358. It carries four partition rows; tile k4, PHASE-BIND and EAST are out; mesh and pin-reg rows are being rebased. HEAD stays in LOOP, as ruled 12:55.
- QC | AT RISK | compose r001 and r002 NOT-READY (b12, b13); r003 began gating 14:44, and a whole gate took 4,133 s earlier; the formal PRE took 3,814 s on 77f2. One more failed round leaves no time for the publish gate. TT is already DEFERRED. If r003 fails, cut the two colliding rows and gate the rest, or 77f2 stays live.
Signed 608 any / 487 current at 14:08 (605 / 484 at 10:05; I did not trace which three records were added); still 0 route confirmations on any live plan.
