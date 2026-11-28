# FABLE-FLOW-1647 (11-27, delta since 14:47): 2 new candidates; open classes S81 56 (flat), HEAD 41 (up 5), QC 46 (flat), KV 38 (up 3), FLEET 20 (up 2)

The rise is registration (CLASS-TRACK-R3 commits 74fe5a7bfdfe, 55177c62fdcf, c20abdec69f2). Candidates per review: 23, 15, 7, 8, 9, 5, 2, 2, 2.
Read from 16:47 hub clock (the hub `date` read 16:50 when I finished), read-only until the publish of this file: CLASSES.tsv with aliases against f548b533676a, CLASS-TREND tail, lanes/posts/COORD.md, CLOSURE.tsv (unchanged since 09:42), 39 post files changed since 14:47.
Not done: sub-lane posts read at 150-330 characters, 12 expanded; VIS-REOWN, FLEET-OPS-R and mq posts skipped; no host sampled; main not checked.
COORD.md's last line is 15:19. Lanes acknowledge "COORD 16:45" rulings that are not in it, so I could not read those rulings (see a2).
Lane-coined names are mapped through the alias column or to the class with the same cause. Format: class | die | evidence | fix | owner lane.

## (a) NEW-CLASS candidates not in CLASSES.tsv (2)
1. P-ROW-SILENT-OVERWRITE | QC (compose is shared) | two rows that were each READY alone collide in the compose and nothing reports it. Second case today on a different key: the STA clk_land_clear CLI row does raw.pop("clk_land_clear") and erases the SU_C clr flag row, so the bt tap stays inside u_bt; only the independent Fable review of r003 saw it (QC-INT-R3 15:50). First case was the landing_contract collision at 13:56, filed then under P-ROW-POSTTAP-REMAP | compose lists every key written by more than one row and fails unless the later row names the earlier one | QC-INT-R3, CLASS-OWNERS-R3
2. P-RULING-OFF-HUB | FLEET | S81-INT-R3 (16:41), QC-INT-R3 (16:42), KV-INT-R3 (16:43) and HEAD-INT-R3 (16:45) all act on "COORD 16:45" rulings while lanes/posts/COORD.md ends at 15:19; a HEAD-PART-R3 sub-agent started ot-push-main on text that claimed a COORD push instruction, and PART refused it (HEAD-INT-R3 16:28, "if COORD did issue it, please say so on the hub"). P-STAMP-DRIFT covers only the stamp | a ruling exists when its line is on the hub; lanes quote the hub line, as S81-INT-R3-SEAM did at 13:07 | COORD

## (b) Classes whose count rose since 14:47
Table moves
1. New rows: HEAD C-DIECLOCK-TRUNK-UNPINNED 1, C-GPL-POSTTD-TAIL-SPARSE 2, C-PERBIT-STATION-MODEL-GAP 2, P-SEAM-UNTIMED-CTL-NSTRIP 1, P-LAUNCH-STAMP-RT-ONLY 1; KV C-FENCE-GEOM-ILLEGAL 8, C-CONE-DEPTH 1, C-TDREPAIR-REGION-MEAN 1; FLEET C-MERGE3-BASE-HIDES-FORK-CONFLICT 1, P-LAUNCH-STAMP-RT-ONLY 1 | owners as in the table
2. P-CLASS-ALIAS-DRIFT | FLEET | 13 -> 20 | registration rule posted 12:52 | CLASS-TRACK-R3
3. P-PLAN-AHEAD-OF-RTL | S81 | 6 -> 7 | t31 ops in every 21:00 form | S81-INT-R3
Rose in posts, table not moved
4. P-PG-OPEN-INSERTED-CELLS | S81 3 -> 4 | native readback of 64 INDEX core ODBs (sha = INDEX sha): 60 pass, 4 FAIL: LLd 596, LLfd 586, LLfu 596 and dsfd_node_NNfd 608 open supply terminals; 19 of 83 unread, no fleet copy (S81-INT-R3-VIEWS 14:57) | DNC HOLD on NNfd; read the 19 from rtx-pro | CLASS-TRACK-R3, COORD
5. P-RUNTIME-MANIFEST | all | report-only ADV-SINKBIN-AGE crashes PRE with a TypeError on four rts (7fb0b8cad197, 7b404ee74012, 92a1ff96b37e, bee94d917e29); cause posted by HEAD at 15:52 (**kw forwarded to census); the "fix or revert in 20 min" of 15:12 has no post. S81 hard_core_built_params.json is curated by hand (VIEWS 15:00) | land the fix; a failing advisory must downgrade, not crash | CLASS-OWNERS-R3
6. C-DIECLOCK-TRUNK-UNPINNED | HEAD 1 -> 4 | Route B k4rb2 failed reach: trunk pin holds (4,944 of 4,944) but 3 tile legs grow to about 480 um because the channel keepout bans every die-clock repeater; MANIFEST slips 03:00 -> 04:30, hard stop 09:00; three sub-rows requested 16:24 | keepout that admits clock repeaters | HEAD-INT-R3 (HEAD-TILE-R3)
7. P-PARENT-STA-MODEL | HEAD | 14 of 28 views stitched into the whole-die STA model are not W12f-form (lane name P-DIE-MODEL-STALE-VIEWS, 15:26); the untimed ctl seams come from the same stale hd_ctl view | refresh views at the first derive after W13 places | HEAD-INT-R3 (HEAD-POCKET-R3)
8. C-TAP-REACH and P-FALSE-GREEN | HEAD | tap models read below CTS on 8 types (378 against 959 um, 283 against 880, 201 against 482; lane name P-TAP-MODEL-UNDERREAD); the density-to-explicit freeze failed review (lane name C-TAP-DENSITY-GROUPED-NOLEVER) | calibrate the model on CTS; C-TAP-REACH-3 row in W13r | HEAD-INT-R3 (HEAD-CASEAM-R4)
9. C-RST-RELAY-REACH | HEAD 10 (table complete 16:26) | worst hd_mesh 690.5 um, hd_st_n4 606, hd_st_k5 537; on hd_st_m the 429 um metric is one combinational path with every hop under 380.4 um, so metric and relay hook measure different things (policy question 15:35) | answer the question, then rows | HEAD-INT-R3
10. C-LEG405 | HEAD, QC | HEAD: 6 near-cap START siblings drafted and gated; hd_serdes relay-to-ring leg 426.7 um with drift; HD-MESH V1 plan-visual BAD and V2 pulled. QC: SU_C p9 flipped leaf_um on 6 per-bit chains, leaves 741-1,399 um from capture, ADV-ISTA-LEAF 0 -> 6 (15:50) | p9b restores leaf_um; mesh V3 in gate | HEAD-INT-R3, QC-INT-R3
11. P-FALSE-GREEN | QC | GENDRY on rt 10c10aeb caps at 24 types and skipped 53 with exit 0; the cap removal ruled at 12:58 has not landed, so QC runs a direct GENDRY on rt a31983a1 per form | remove the cap; a skip fails the gate | CLASS-OWNERS-R3
12. C-REPAIR-BUF-OVER-MACRO | KV 19 | first hook left 1,893 cells with no legal exit; displacement 255.5 -> 131.9 um against a 50 um gate; row DEFERRED 11-28 | v2 on main 096f4972166, probe running | KV-INT-R3
13. C-XDIE-ABI-MISMATCH | KV, QC | HUB r23f lengthens 132 of 2,840 KV lanes by 233 lane-cycles, 6 of them into the D2D bridge; peer_abi checks codec and KP4 only, no tool checks a lane-latency term; QC's "no dependency" (16:45) is from grep, not simulation | add the latency term to peer_abi, or defer HUB | KV-INT-R3, QC-INT-R3
14. P-INPUT-RECEIPT | S81 | D3 sealed tree was not replicated to epyc12 (host list edited in the wrong script); the bind died in 4 s at 15:11 and the cause was posted at 16:41 | replicate check before launch; a waiter on every cut-critical job | S81-INT-R3
15. P-DEAD-LANE-ROUTING | FLEET | the new WAIT-STATE post (0d265c348115) sends all 28 s81_head lines to S81-INT-R3 (14 WAIT-FORM, 14 WAIT-PLAN-VISUAL); QC gets 51; 79 lines in 2 h | map die s81_head to HEAD-INT-R3 | FLEET-OPS-R5
16. P-POSTPUBLISH-DISK | FLEET | localhost / at 98 %, 85 GB free, 39 GB of it one session scratchpad of clones and kit copies (KV-INT-R3 15:04); epyc7 96 % with 2.4 TB under wave markers; 39 GB raw rsync on epyc11 (relinked) | see c5; epyc7 after the cut | FLEET-OPS-R5
17. P-AUTOMERGE-REVOKE-RACE | HEAD | the relayed push approval in a2 | - | COORD
Down: job deaths 34 in 2 h with 6 SETUP or NOT-RUN (31 in the 2 h before); LEC 54 of 54 EQUIVALENT; C-HOLDCHAIN and KV clock contract closed; KV FENCEGEOM cleared in core8 (PRE 0 findings); P-WAIT-STATE-SILENT and P-WAVE-ALLOWLIST-STALE fixes on main; signed 608 any / 487 current, flat.

## (c) Items with no live owner
1. CLASS-OWNERS-R3 has not posted since 14:51 | it holds b5, b11, the clk_land_clear --rt default, the PRE placed calibration (QC 15 types, S81), the tap-model calibration and the START no-port WARN | confirm live or restart | COORD
2. dsfd_node_NNfd DNC HOLD request (14:53) | COUNT-DO-NOT-COUNT.tsv unchanged since 10:55; the core is in the INDEX | CLASS-TRACK-R3
3. 19 INDEX S81 cores unread for open PG | "owner COORD", need rtx-pro | COORD
4. Requests with no hub answer | HEAD-INT-R3 15:35 (reset-reach policy), 16:24 (three sub-rows), 16:28 (was a push instruction issued); HEAD-CASEAM-R4 16:19 and HEAD-EAST-R4 15:05 (C-GPLTD-DROPS-LOGIC-CLUSTER, fixed 7b404ee74012) class filings; KV C-FWDCLK-PHASE-BALANCE (alias of C-FWDCLK-WRONG-TAP or own row) | COORD, CLASS-TRACK-R3
5. Localhost scratchpad, 39 GB | KV-INT-R3 cannot remove it within the rules | FLEET-OPS-R5
6. PROGRESS-WATCH TICK-DEAD 15:36 (no tick line for 24 min) | no answer; KIT-WAVE lines resumed by 16:31 | FLEET-OPS-R5 confirms cause
7. 28 HEAD wait states nobody at HEAD was told about (b15); 36 QC WAIT-PLAN-VISUAL and 15 WAIT-VISUAL | HEAD-INT-R3, QC-INT-R3
8. QC fe_cl95cd1d0c: DRT ended at 7 violations, ECO attempt 1 of 1; the waiter addresses dead QC-INT-R2 | QC-INT-R3
9. PLAN-GATE-PRE WAITER-FAIL 5da0b183b934 (14:52) on a HEAD result that is a CLOSED-SUPERSEDED verdict | the substring fix still misfires | FLEET-OPS-R5
10. epyc7 2.4 TB: each die must name superseded attempts after the cut | no sub-lane named | INT-R3 lanes
11. Four owner questions from 09:17; TOKEN waits on the 11-28 KV regen; HBM parked

## (d) 21:00 cut risks per die
- S81 | MEDIUM | D3 5331bea82ed4 passed all four gates (15:00) but its sealed-tree bind lost 85 min (b14) and restarted 16:36; still to do: bind and LAT, four-host copy, publish_gate with per-type topology (the sweep took 3,458 s at 12:29), apply. The stated fallback point of 20:30 is too late to seal and gate D2 or D162: decide by 18:30, or seal D2 in parallel now.
- HEAD | LOW for the cut, HEAD stays in LOOP | W13q 148712eff5f7 is staged, publish_gate PASS (16:36), guarded apply at 21:00:20. Risks: the late swap to W13r (two more rows, compose started 16:45) and another launch-stamp collision on the shared pubgate dir. Tile, PHASE-BIND, EAST and mesh are out; die clock due 04:30.
- QC | MEDIUM, much better than at 14:47 | C2 r001 (TT + 5 rows) READY with direct GENDRY PASS; D r001 READY, GENDRY running, being packaged as fallback. Risk: round 2 on C2 at 17:30 adds three rows, then GENDRY and publish_gate (the formal PRE took 3,814 s on 77f2) land near 20:30. Freeze round 2 at 18:45 or publish r001. epyc8 has 224 GB free against a 205 GB reserve.
- KV | MEDIUM | core8 898c3f1ef405 (10 rows, 434 keys) launched 16:08 as one run: compose, build, G0, bind, LATCHECK, PRE, GENDRY; no result at 16:47. Fallback core8n (8 rows, no HUB) is only dry-composed, and its 20:30 trigger is too late to gate. b13 is unchecked by any tool. sys_c stays held from kits; FIRM and the repoint are out.
- All dies | no gate may move to current main while b5 is open; every form is pinned to an older rt (S81 779cd222ef5e, HEAD b71c5218e0b5, QC a31983a1, KV dd297e399df5), so a late fix cannot be picked up tonight.

Counts: new classes 2; risen classes 17 (3 table moves, 14 from posts); unowned items 11.
