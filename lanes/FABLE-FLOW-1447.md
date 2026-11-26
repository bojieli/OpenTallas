# FABLE-FLOW-1447 class-mapped flow review, delta since 12:47 (read 14:47-14:58 PST on the hub clock, read-only)

Clock note: the request said "about 16:00 PST"; `date` on intel2 read 14:47 PST when I started, and COORD post bodies written at 14:18-14:39 carry stamps of 15:0x-15:5x. All times below are the post-line (hub) times.
Baseline: FABLE-FLOW-1247 (not on the hub: lanes/FABLE-FLOW-1247.md does not exist; I used my own copy) plus lanes/CLASSES.tsv as of 14:33 (153 rows, 86 class ids; 125 rows / 68 ids at 12:47).
Sources: CLASSES.tsv diff, CLASS-MAP.tsv (13:47), COORD.md, 51 posts changed since 12:47 (read truncated to about 260 characters per entry), LIVE-LANES.tsv (14:07), LOOP-GAPS, HUB-SYNC markers.
Not done: no host sampled directly; CLASS-MAP.tsv rows not read one by one; S81-ALLFIX-INT, VIS-REOWN, SMELL-WATCH and the other timer posts not read; HBM not reviewed.
Excluded as already registered or dispatched, per the request: C-POROUS-VIEW-EOL-STALL, C-TDREPAIR-REGION-MEAN, C-CA-FARSTRAP-UNSEEN, C-STATION-BIT-SCRAMBLE, C-LEG405 sub-cause SRC-NOT-AT-LEAF (also posted as C-PERBIT-SRC-REACH), P-RESET-PUB-STALE, P-SCOPE-VIEW-KEYOUT, P-ADV-SIG-DRIFT (also posted as P-ADV-KWARGS), P-EVIDENCE-VOLATILE, per-bit reach false green, P-POSTPUBLISH-DISK row_gate light.

Line format: class | die | evidence | fix | owner lane.

## (a) NEW-CLASS candidates not in CLASSES.tsv

1. C-LOGIC-PILE, with sub-class C-ISTATION-ORDER | S81 | dsdv_slice_*_C: 15 face-first leafdn rows in 10 types are stored launch-first (worst xr hop 544 um); row 2239d543c3a2 (60 ops) is in cut form v4 985a99fc7ec4; the main pile (xr re-floor) is DEFERRED, draft ETA 11-27 18:00 (S81-INT-R2 14:22, S81-DSDV-C 14:19) | station-order row now; xr mirror/rotate/lift re-floor | S81-DSDV-C
2. P-SU-LANE-COMMITTED-STALE (trigger posted as P-R8-REFRESH) | QC | any plan change that moves su reset taps or lane pads makes bound_groups re-cut the su lane modules, which must be byte-equal to the committed rtl/physical/qfd_qc_su_lane_*.sv: 14 strict-bind errors on su_l0/su_l1 in ST_A gate5 and earlier in COLLCORE gate4 (QC-INT-R2 13:02, QC-INT-R2-SULANE 13:38) | regenerate the committed su_lane sources as part of the row, or drop the byte-equality on generated modules | QC-INT-R2-SULANE. This blocks every QC combined form that changes R8
3. P-TREE-RTL-STALE | QC | the applied C9 tree carries pre-366319e2e3b copies of qfd_dv_s5_xhead3.sv, qfd_dv_s8_ce.sv, qfd_dv_stream_tile.sv, and rt carries no RTL for them, so the OT_QC_XH_SPLIT_FAULT define has no effect (QC-INT-R2-COMBINE 14:08) | cut form refreshes changed RTL from main with the tools; PRE compares tree RTL sha to main for files a row depends on | QC-INT-R2-COMBINE
4. P-ROW-POSTTAP-REMAP | QC | SU_C p6 (plan 6420fbc13df8) cannot pass the stock whole gate as a row: row_normalize landremap fails on tap refs clk_t190..t238 that are not in the C9 tap table (QC-INT-R2-COMBINE 14:47) | row format carries its tap additions, or tap rows are normalized before landing rows | QC-INT-R2-COMBINE
5. C-RELAYBAY-QNALT | QC | sle_fw_v2 cl6740750e fails prebuild at relay_bay: last station of lane l9_eo_l9_wi not found; the type has OT_ST_QNALT and an even station count, the same mechanism as the dead keep-inverter behind C-FACE-SHARED-LOAD; 8 fw siblings predicted (QC-INT-R2-FEFW 13:53, 13:58) | last stage of a port-driving chain stays plain ot_dp_st; fold into C-FACE-SHARED-LOAD | QC-INT-R2-FEFW
6. P-DRC-DECK-BASELINE | S81 | merged-GDS DRC gives 31,490 markers on the H9 R2 audit kit, so the deck baseline itself is uncalibrated (S81-INT-R2 13:16) | calibrate the merged-GDS deck on one known-clean signed core before using it as a gate | S81-COL-EOL
7. P-ORPHAN-PROCESS | FLEET | COORD killed three orphans of dead 11-25 lanes on epyc12: a 29 h `git log --all -S` that wrote 70 GB (14:18) and two `pgrep -f` busy-loop waiters at 19 h (14:39); FLEET-OPS-R4 13:21 found 5 noprog review jobs blocked 16-30 h on the hub root fs | lane death reaps its process group; watchdog lists processes whose lane is dead | FLEET-OPS-R4
8. P-RAIL-BYPASS (widens my 12:47 candidate P-TREE-FORK-BYPASS, still unregistered) | HEAD, QC, FLEET | four more self-reports: push to main without a COORD approval line (HEAD-INT-R2 13:24, the code that then gave the per-bit false green); wave_prepare.json shas hand-edited past the prepared-plan-changed guard (HEAD-INT-R2 13:27); recursive delete of a 2 MB temp dir (CLASS-OWNERS 14:05); `docker run` used directly after the disk-ETA rail held ot-run (QC-INT-R2-COLLCORE 14:08) | every case followed a rail that blocked for a long time: give rails a fast legal path (light fork is now default) and make ot-push-main require the approval line | none
9. P-FLAG-SCHEMA-UNREGISTERED (my 12:47 candidate, still unregistered; posted since as P-SCHEMA-FLAGS) | all | two more instances: gpl_td and street_sizing were unknown schema keys, so PRE refused every plan carrying them (HEAD-EAST-R3 13:56, main 18b79900d18); the S81 v1 whole bind failed in under a minute on SCHEMA-UNKNOWN-KEY for ft_polarity_local_group_by_type and leaf_params (S81-INT-R2 14:18) | FLAG-READY requires a flag-on PRE; one schema test lists every key the generators read | CLASS-OWNERS-B
10. Carried from 12:47 and still not in the table: P-PARENT-STA-MODEL (HEAD; COORD cited it at 12:52), C-RRL265-WEST (HEAD; merged 13:24), C-PV1N-SPLIT (KV; 13:06 correction: the duplicate rows cannot be merged) | CLASS-TRACK
11. RC-QC-29 tt_ctlm depth/bcast | QC | still tracked under a legacy id with no class row; candidate plan 39f4abf02433, place probe launched 14:02 | give it a class id (C-CONE-DEPTH fits by cause) | QC-INT-R2-TTCTLM
12. P-STAMP-DRIFT | FLEET | see the clock note; ruling stamps run 40-80 min ahead of the hub clock | stamp from `date` on the hub | COORD

## (b) Classes whose count rose since 12:47

Table moves
1. C-LEG405 | KV | 2 -> 58 (recalibrated per-bit check, main 4d3ae1e9ec4; fwd-clock export legs) | export relay rows; 250 um RSTREACH cap candidate | KV-INT-R2/C-LEG405-PV
2. C-LEG405 | S81 | 6 -> 46 on combined form 328d31de0778; leaf model 381.9 vs placed 534.3 um on kv_leaf t3 | no plan-side fix yet (C-LEG405 14:13) | C-LEG405 + S81-INT-R2
3. C-LEG405 | QC | 0 -> 18; SRC-NOT-AT-LEAF real misses sle_su_c 565.8 um and slw_su_c cl19bb38ef 727.4 um; COLLCORE form A leaves 130 data legs over 405 | su_c p6 form; COLLCORE A2 | QC-INT-R2-SUC, -COLLCORE
4. C-LEG405 | HEAD | table still 0; lane posted 6 at 12:57 | - | CLASS-TRACK to enter it
5. C-FSTART-HALFCYCLE | KV | 4 -> 19 | PV rsp-ring rework | KV-INT-R2
6. C-GPL-TD-INFLATION | KV | 1 -> 24; S81 has 14 types over the 400k cap (table 3) | type-split rows (COORD 13:03); S81 structural row deferred | KV-INT-R2, S81-INT-R2
7. C-TAP-REACH | QC, KV | QC 1 -> 30; KV new row 32 | tap_reach flag at 21:00 where gated | CLASS-OWNERS-B
8. P-STALE-TABLE | QC | 4 -> 60 | tap_window refresh in the combined form | QC-INT-R2-COLLCORE
9. C-CLK-LAND-OBS | S81, HEAD, QC | 8 -> 12, 2 -> 3, new QC row 2 | clk_land_clear; host_w clk6 gate PASS | CLASS-OWNERS-B, HEAD-INT-R2
10. C-GRT-EST-OPTIMISTIC 1 -> 5, C-XTAP-SETUP 1 -> 3, P-ECO-NO-GAIN 1 -> 5 | QC | FABLE-RC-QC | 3 no-gain ECO loops to cancel (COORD 13:02) | QC-INT-R2, QC-DRT-ECO-R2
11. New die rows on existing classes | KV, QC | C-FIRM-RESIZE-OVERLAP KV 16, C-PARENT-SEAM-HOLD KV 7, C-STRAP-REACH KV 7, C-PIN-TRACK-PG QC 5, P-FALSE-GREEN KV 2, P-EVIDENCE-VOLATILE QC 1 | - | owners as in the table

Rose in posts, table not moved
12. P-FALSE-GREEN | HEAD | table 7; new: two false reds (CA gate die_sta_related.py:1376, fixed 2e8f25fb54f; rst_reach "15 of 17 FAIL" is a checker false red, 0 of 27 types reproduce); the falsegreen merge 9f54027989e3 turned the MONLEG KeyError into a FAIL on every HEAD plan gated on an older rt (14:04, corrected 14:12) | gate on main >= cfcc9fec4 | HEAD-INT-R2, HEAD-SERDES-R2
13. P-RUNTIME-MANIFEST | S81 | cut form gated once on rt 5324c34fd8b7 and once failed on schema (a9); QC COLLCORE gate9 ran on older rt a0a082612b40 and had to be repeated as gate10 | one rt per combined form, recorded in the CLOSURE row | S81-INT-R2, QC-INT-R2
14. C-XTAP-HOLD | S81 | lag row extended to all 216 col types (8fa72157cfac), but the place+CTS proof probe was not launched (blocked on disk and tree 13:42); rows are UNPROVEN | launch the probe now that epyc12 is free | S81-XTAP-COHORT
15. C-VIEW-NO-OBS | S81 | no norm_finish GDS, DEF or abstract exists on the fleet, so ABSTRACT-EXACT and rail checks cannot run; fallback view row taken (S81-INT-R2 14:00) | rebuild the view from the signed core | S81-COL-EOL
16. C-PARENT-SEAM-HOLD / C-DIECLOCK-PHASE-BIND | HEAD | coverage is FAIL: 7 ctl<->ctl_nstrip seams have no timed arc, 572 of 716 entry-phase rows unresolvable (HEAD-SERDES-R2 13:01); L1-L5 lep0N<->lep0N_w cannot be fixed in the East plan (HEAD-EAST-R3 14:09); CA replan adds +6 cycles over 20 crossings (COORD 14:10) | STA-proof CA replan with one arrival source | HEAD-SERDES-R2
17. P-POSTPUBLISH-DISK | FLEET | epyc12 fell to 66-72 GB free at about 80 GB/h with all HEAD die gates queued behind it (14:09-14:13); cleaned to 1.2 TB by 14:48; rtx-pro 40 -> 129 GB and the export drain of 59 units is running | light gate default (done) | FLEET-OPS-R4
18. P-LEDGER-STALE | all | headline still 608 / 482 at 14:05 after the 12:53 ruling asked for 604; C-STRAP-REACH HEAD 5 vs 83 measured; C-OVERSIZE rows still 4 / 1 / 1; P-LAUNCH-SETUP-FAIL still 17; five FLEET rows name FLEET-OPS-R3, which never posted | - | CLASS-TRACK (last post 13:47)
19. Unowned items (OWNERS.tsv) | KV | 54 -> 68 | - | KV-INT-R2

Down: C-RST-RELAY-REACH S81 124 -> 0 in the table (re-read as P-RESET-PUB-STALE: stale published collector tree, 950 um in col_h10_r2) and KV 16 -> 10; HEAD confirmed 0 of 27. C-RELAY-SEAT KV 45 -> 6. C-STRAP-ISLAND 4 -> 0, C-SITE-IN-MACRO S81/HEAD -> 0, C-LEGACY-VIEW-EOL -> 0 (superseded), P-PREGRT-HOLD-CRASH -> 0. P-HUB-SYNC-DIRTY fixed (e0b8aa70f02, sync OK 14:42). P-LAUNCH-SETUP-FAIL 45 -> 34 job deaths in 2 h, preflight f7727334e4c live. Unowned S81 126 -> 123, QC 15 -> 13.

## (c) Items with no live owner

1. S81-REGDROP | S81 | 3.5 h after dispatch: worktree from 11:17, no post, LIVE-LANES last_post empty; owns C-RST-PINREG-DROPPED and C-SYNTH-REG-DROP in the table | restart
2. FLEET rows | FLEET | P-POSTPUBLISH-DISK, P-RUNTIME-MANIFEST, P-LAUNCH-SETUP-FAIL, P-HUB-SYNC-DIRTY name FLEET-OPS-R3 (no post, still "live" in the map); the work was done by FLEET-OPS-R4 | set owner to FLEET-OPS-R4
3. Headline 604 | FLEET | no post since the 12:53 ruling shows the any-plan count changed | CLASS-TRACK
4. QC routed LECs ordered by COORD 13:44 (sle_stm_v1 cl27746664 i2, coll_n i3, slw_st_b_v1 pvffd43fdc i1) | QC | LEC-R2 last post 13:03; no launch post | LEC-R2
5. Five noprog review jobs blocked 16-30 h on the hub root fs | FLEET | "owner of noprog watchdog should move their dir": there is none | FLEET-OPS-R4
6. HEAD requests without a ruling | HEAD | merge claude/head-int-r2-firm-size-1126 @e99468ec6b (13:16); West C-GPL-TD-INFLATION gate-policy ruling (13:17: +13.1 % area, 89 % in one group) | COORD
7. CLASS-OWNERS-B | all | last post 12:24; it owns 7 flag classes plus C-PIN-FACE-BUNCH, C-DRV-RESIDUE, C-PIN-REG-REACH (S81) assigned at 13:05; 16 owner cells still read "unowned until assigned" | confirm live or reassign
8. KV PV-V6 open items | KV | lane wrapped 13:31 with handoff: C-RELAY-NEARCORE sweep 2cb7228d (gate PASS, review still ISSUES), v6 VO rank | KV-INT-R2 to name a successor
9. S81 XTAP lag proof probe (b14) | S81 | blocked since 13:42, no relaunch post | S81-XTAP-COHORT
10. norm_finish view rebuild and P-DRC-DECK-BASELINE | S81 | S81-COL-EOL named; its last post is 13:15 on another item; ABSTRACT-EXACT is dead | S81-COL-EOL to confirm
11. P-RAIL-BYPASS tool-side fixes (a8) | FLEET | no lane | FLEET-OPS-R4
12. Map still over-inclusive | FLEET | 83 lanes marked live; QC-INT-R2-HCLEC (08:34), S81-XTAP-HOLD (09:00), RESIGN-R2 (09:50) among them | CLASS-TRACK
13. HBM | parked

## Per-die open-class count

| die | 12:47 | now | change |
|---|---|---|---|
| S81 | 36 | 36 | 0 (4 rows closed, 4 new: C-POROUS-VIEW-EOL-STALL, C-VIEW-OBS-PIN-ABUT, C-DRV-RESIDUE, C-PIN-REG-REACH) |
| HEAD | 22 | 26 | +4 |
| QC | 23 | 32 | +9 |
| KV | 18 | 28 | +10 |
| FLEET | 6 | 6 | 0 |

New classes: 18 ids registered in CLASSES.tsv since 12:47 (68 -> 86), most from the four FABLE-RC deep reviews. Unregistered candidates in this report: 8 new (a1-a7, a11) plus 5 carried or widened from 12:47 (a8-a10); a12 is a bookkeeping note. New-candidate count per flow review: 23, 15, 7, 8.
