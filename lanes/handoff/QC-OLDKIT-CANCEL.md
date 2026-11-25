# QC-OLDKIT-CANCEL handoff (lane memory)

Census 2026-11-25 ~05:25 PST. Source: live `oth-*` user units on intel1/2, epyc2/7/8/9/10/11/12. Each unit's cgroup procs were
matched to a qwen_compute kit path; DRT counts are from run/logs/asap7/*/base/5_2_route*.log ("Number of violations" per iteration);
GRT numbers are from 5_1_grt.log (OT_REPAIR_STALL setup/hold after repair). 114 live QC units; all are on block s29q103S4Q9N46R6V4
(pre-C1o) except as noted. Cancel gate: C1o v13 aa3a14fb7484 BIND-PASS (not yet posted at census time).

## CANCEL (over 3 h, measured flat DRT at a high count; not a QC-DUP-KITS type)
| host | unit | age h | kit | DRT per iteration | GRT after repair | evidence |
|---|---|---|---|---|---|---|
| epyc10 | oth-ubuntu-2179782-1795542318 | 19.6 | items/sle_fw_v2__cl6740750e | 416066, 152884, 121450, it3 at 60% = 93844 | setup +69.5, hold fixed (ws 33.9) | DRT started 20:06 PST; 9.3 h for 3 iterations (~2.5 h each); the it3 collapse every converging kit shows (to below 30k) is absent; it1->it2 -21%. sle_fw_v2 is in the C1p FWV2/OVERSIZE rows. |
| intel1 | oth-ubuntu-1377941-1795524507 | 24.6 | items/slw_fw_v2__cl8f84514c | 398476, 104690, 71761, 16353, 11640, 9928, 8775, 8323 | setup +85.8, hold ws 18.2 | it3->it6 -46% (<70%); it6->it7 -5%; 8.3k after 8 iterations |
| epyc9 | oth-ubuntu-819767-1795547628 | 18.1 | private/QC-ALLFIX/sle_fe_v2_1124081835 | 474459, 162913, 125492, 62620, 55115, 51554, 48902, 47387, 45768, 43279, 36163 | setup -33.6, hold ws 8.5 | it3->it6 -22%; 36k after 10 iterations |

## Deferred to QC-DUP-KITS (types sle_sc_v1, sle_fe_v1, slw_fe_v1, slw_sc_v1, slw_su_l1); numbers for that lane, no action here
| host | unit | age h | kit | DRT (latest iterations) |
|---|---|---|---|---|
| epyc7 | oth-ubuntu-2782498-1795505868 | 29.8 | private/QC-OPEN-SU/sle_sc_v1__cl115da35f_1123214858 | it16 2761, it17 13398, it18 5839 (3->6 -44%) |
| epyc7 | oth-ubuntu-4029420-1795519597 | 25.9 | private/QC-OPEN-SU/sle_sc_v1__cl115da35f_1124012159 | it13 5691 (3->6 -38%) |
| epyc2 | oth-ubuntu-3997324-1795524415 | 24.6 | items/sle_sc_v1__cl115da35f | it16 6215, it17 33693 (3->6 -33%) |
| epyc7 | oth-ubuntu-1934637-1795524432 | 24.6 | items/sle_sc_v1__cl7479a5ec | it10 15333 (3->6 -29%) |
| epyc8 | oth-ubuntu-46526-1795536673 | 21.2 | private/QC-ALLFIX/sle_sc_v1__cl7479a5ec_1124053232 | it8 24770 (3->6 -24%) |
| epyc7 | oth-ubuntu-2030663-1795524619 | 24.5 | items/slw_sc_v1__cl64543eaf__cl4590432d | it12 7139 (3->6 -40%) |
| epyc8 | oth-ubuntu-4162619-1795536591 | 21.2 | private/QC-ALLFIX/slw_sc_v1__cl64543eaf__cl4590432d_1124054102 | it8 14524 (3->6 -34%) |
| intel1 | oth-ubuntu-1318463-1795524322 | 24.6 | items/sle_fe_v1__cl8210183c | it2 55124 (slow, it3 running) |
| epyc8 | oth-ubuntu-4099462-1795536522 | 21.2 | private/QC-ALLFIX/sle_fe_v1__cl8210183c_1124052744 | it8 8478 (3->6 -41%) |
| epyc11 | oth-ubuntu-59304-1795541430 | 19.9 | private/QC-ALLFIX/sle_fe_v1__cl1cbb7497_1124052207 | it18 90, still falling |
| epyc8 | oth-ubuntu-4037539-1795536466 | 21.3 | private/QC-ALLFIX/slw_fe_v1__cl95cd1d0c_1124052635 | it6 5291 |
| epyc10 | oth-ubuntu-3727046-1795546147 | 18.6 | private/QC-ALLFIX/slw_fe_v1__clfe325744__cldb4efe33_1124082623 | it13 1960, falling |
| epyc9 | oth-ubuntu-626515-1795547086 | 18.3 | private/QC-ALLFIX/slw_fe_v1__clfe325744__cl08d14f0d_1124082533 | it47 4 (near zero) |
| epyc8 | oth-ubuntu-3976397-1795536410 | 21.3 | private/QC-ALLFIX/slw_su_l1__clcc9d0155_1124052823 | it16 8519, it17 40739 (3->6 -29%) |
| epyc7 | oth-ubuntu-3731323-1795587855 | 7.0 | private/QC-ALLFIX/slw_su_l1__cla2a78701_1124082633 | it1 101290 |
| others | sc/su_l1 relaunches 1124144612/144713/145502/145602/145701 (epyc7, 3.9-6.9 h) | | | in GRT / early DRT |

## The 11 st_b private run-items (QC-ALLFIX scope add 05:3x): all KEEP
All 11 finished main route at DRC 0 (5_2_route.log final 0). 6_finish worst setup is shown below. Each is now in its post-route hold ECO (prd), and its log updated in the last 10 min.
| host | unit | kit | route final | 6_finish setup | stage | verdict |
|---|---|---|---|---|---|---|
| epyc8 | oth-ubuntu-3979366-1795536412 | sle_st_b_v1__pvc5a85fd4__pv38472fb8_1124053346 | 1,1,0 | +18.1 | prd i1 hold | KEEP |
| epyc8 | oth-ubuntu-3989410-1795536420 | sle_st_b_v2__cl14c98df5__pv41c959f3_1124053423 | 1,1,0 | +14.1 | prd i1 | KEEP |
| epyc8 | oth-ubuntu-3999836-1795536430 | sle_st_b_v2__clfde1249e_1124053500 | 14,14,0 | -20.9 (TNS -115.6) | prd count p1 | KEEP (inside -42) |
| epyc8 | oth-ubuntu-4019854-1795536447 | slw_st_b_v1__cl6357f1cc__pv6ace3e48_1124054213 | 1,1,0 | +9.0 | prd i1 | KEEP |
| intel1 | oth-ubuntu-2846716-1795540097 | slw_st_b_v1__cl6357f1cc__pvffd43fdc_1124055000 | 1,1,0 | +44.1 | abstract/report | KEEP |
| epyc11 | oth-ubuntu-273908-1795542052 | sle_st_b_v1__pv0e7b1dcc_1124053259 | 3,3,0 | +42.6 | prd i1 route (11 viol) | KEEP |
| epyc11 | oth-ubuntu-53930-1795541420 | sle_st_b_v1__pvc5a85fd4__pv7b7fafb4_1124053350 | 1,1,0 | +17.6 | prd i1 route (3 viol) | KEEP |
| epyc11 | oth-ubuntu-340651-1795542236 | slw_st_b_v1__cle6023ec2_1124054248 | 9,9,0 | +2.0 | prd count p1 | KEEP |
| epyc11 | oth-ubuntu-315774-1795542169 | slw_st_b_v2__pva66d0f22__pvb80e2003_1124054325 | 3,3,0 | +36.2 | eco_loop: signoff PASS rows; related-pair skew 92.8>80 advisory | KEEP |
| epyc7 | oth-ubuntu-1876640-1795540267 | sle_st_b_v2__cl14c98df5__pvcd986c42_1124053442 | 32,1,0 | +35.2 | prd i1 route (65 viol) | KEEP |
| epyc7 | oth-ubuntu-2015692-1795540528 | slw_st_b_v2__pva66d0f22__pv3d7bec84_1124055051 | 1,1,0 | +17.2 | prd finish | KEEP |

## KEEP (notable; the rest are hc/stm/st_b/st_a/cb/coll in GRT, prd or sign-off with DRT at or near 0)
- intel2 oth-ubuntu-528313-1795541716 items/slw_fe_v2__cle312294d: it15 995, falling about 30% per iteration; GRT setup -48.8 (between -42 and -300, never cancelled).
- epyc10 oth-ubuntu-3748913-1795546209 private slw_fe_v2__cle312294d_1124082715: it1 109612, it2 at 60% 94006. Unmeasured (DRT started 21:51 PST). It duplicates the intel2 wave kit, which is far ahead: QC-DUP-KITS to decide.
- epyc10 oth-ubuntu-3686683-1795546017 private slw_fe_v2__clf110fab2_1124082809 (owner QC-FEV2-F110): it1 30867, unmeasured.
- intel1 oth-ubuntu-4033076-1795553498 sle_su_l0__cl086d85ba: has sat at 1 violation from it19 to it40. Near zero, KEEP; the DRV ECO should fix the 1.
- epyc11 oth-ubuntu-489710-1795557148 items/sle_hc0__cl05696ed1 attempt_2: DRT 0. hc0 family: all near 0.
- V3-block ECOs: intel1 oth-ubuntu-2841461-1795408595 items/sle_fw_v1__clf58b4dfb (56.8 h, prd), epyc11 QC-STATION-REGEN x3 (oth-ubuntu-1015934/1087674/1260338, 32 h, prd). These are ECOs, so not cancelled.

## Flag (out of scope, no action): 10-day-old S2 LEC-async waiters, epyc8
oth-ubuntu-3135343-1794696222, oth-ubuntu-3142624-1794696238, oth-ubuntu-2063722-1794715554: s29q103S2 sle_hc2 attempt_8.
Each has been in the lec_async `sleep 5` loop since 11-14/15, with its route log untouched for 10 days. They use almost no CPU or RAM. Owner: COORD/KV? (QC wave). Not a route kit.

## REVISION 05:4x (QC-ALLFIX rulings + full SMELL coverage)
The rows below cover all 48 QC DRT SMELL rows in lanes/SMELL.tsv, which reduce to 21 distinct kits. The census covered every live QC unit, 114 in all; that includes every old-block route kit over 12 h.
Columns: it0 | last completed iteration | fall over iterations 3-6 | GRT setup after repair | verdict.
| kit | host/unit | it0 | last | fall 3-6 | setup | verdict |
|---|---|---|---|---|---|---|

| private sle_fe_v2_1124081835 | epyc9 oth-ubuntu-819767-1795547628 | 474459 | it10 36163 | 22% | -33.6 | CANCEL after BIND-PASS |
| items/slw_fw_v2__cl8f84514c | intel1 oth-ubuntu-1377941-1795524507 | 398476 | it7 8323 | 46% | +85.8 | CANCEL after BIND-PASS, once QC-FWV2-BAY OKs it or 30 min pass |
| items/sle_fw_v2__cl6740750e | epyc10 oth-ubuntu-2179782-1795542318 | 416066 | it2 121450 (it3 ~94k at 60%) | not reached | +69.5 | KEEP (ruling), handed to QC-FWV2-BAY (<5% next drop rule) |
| items/slw_fe_v2__cle312294d | intel2 oth-ubuntu-528313-1795541716 | 367946 | it15 995 | 51% | -48.8 | KEEP, still falling ~31%/iter (1440->995) |
| private slw_fe_v2__cle312294d_1124082715 | epyc10 oth-ubuntu-3748913-1795546209 | 378938 | it1 109612 | not reached | +101.9 | KEEP, unmeasured |
| private sle_su_l0__cl086d85ba_1124115227 | intel1 oth-ubuntu-4033076-1795553498 | 187976 | it39 1 | 58% | +149.0 | KEEP, near zero |
| private sle_sc_v2_1124052934 | - | 412199 | - | 9% (SMELL) | - | N/A, not live |
| items/sle_fe_v1__cl8210183c | intel1 oth-ubuntu-1318463-1795524322 | 317907 | it2 55124 | not reached | +120.2 | QC-DUP-KITS |
| private sle_fe_v1__cl8210183c_1124052744 | epyc8 oth-ubuntu-4099462-1795536522 | 320246 | it8 8478 | 41% | +164.3 | QC-DUP-KITS |
| private sle_fe_v1__cl1cbb7497_1124052207 | epyc11 oth-ubuntu-59304-1795541430 | 329677 | it18 90 | 50% | +139.4 | QC-DUP-KITS (falling, near zero) |
| items/sle_sc_v1__cl115da35f | epyc2 oth-ubuntu-3997324-1795524415 | 521993 | it17 33693 | 33% | +104.7 | QC-DUP-KITS |
| items/sle_sc_v1__cl7479a5ec | epyc7 oth-ubuntu-1934637-1795524432 | 510309 | it10 15333 | 29% | +108.5 | QC-DUP-KITS |
| private sle_sc_v1__cl7479a5ec_1124053232 | epyc8 oth-ubuntu-46526-1795536673 | 478667 | it8 24770 | 24% | +95.6 | QC-DUP-KITS |
| private QC-OPEN-SU sle_sc_v1__cl115da35f_1123214858 | epyc7 oth-ubuntu-2782498-1795505868 | 490378 | it18 5839 | 44% | +107.9 | QC-DUP-KITS |
| private QC-OPEN-SU sle_sc_v1__cl115da35f_1124012159 | epyc7 oth-ubuntu-4029420-1795519597 | 504597 | it13 5691 | 38% | +109.0 | QC-DUP-KITS |
| items/slw_sc_v1__cl64543eaf__cl4590432d | epyc7 oth-ubuntu-2030663-1795524619 | 457993 | it12 7139 | 40% | +73.2 | QC-DUP-KITS |
| private slw_sc_v1__cl64543eaf__cl4590432d_1124054102 | epyc8 oth-ubuntu-4162619-1795536591 | 450083 | it8 14524 | 34% | +112.0 | QC-DUP-KITS |
| private slw_fe_v1__cl95cd1d0c_1124052635 | epyc8 oth-ubuntu-4037539-1795536466 | 266434 | it6 5291 | 55% | +150.7 | QC-DUP-KITS |
| private slw_fe_v1__clfe325744__cl08d14f0d_1124082533 | epyc9 oth-ubuntu-626515-1795547086 | 274895 | it47 4 | 50% | +21.9 | QC-DUP-KITS (near zero) |
| private slw_fe_v1__clfe325744__cldb4efe33_1124082623 | epyc10 oth-ubuntu-3727046-1795546147 | 272423 | it13 1960 | 41% | +158.6 | QC-DUP-KITS |
| private slw_su_l1__clcc9d0155_1124052823 | epyc8 oth-ubuntu-3976397-1795536410 | 274214 | it17 40739 | 29% | +18.9 | QC-DUP-KITS |
Check 2:
- Neither CANCEL type is in a QC-DUP-KITS set.
- sle_fe_v2 and slw_fw_v2 are in neither the C1o launch list nor c1o_full_route nor probe_from_held (QC-C1O-COMPOSE-launch-list.json); both are HELD for C1p rows (FEFW-FAM / FWV2).
- So neither cancel removes the only live kit of a C1o launch type.
S2 epyc8 LEC-async units: now owned by this lane (ruling 4); investigation in progress.

## Log
- 05:2x census + classification. Waiter armed for "BIND-PASS C1o v13 aa3a14fb7484" in lanes/posts/QC-C1O-COMPOSE.md.
- 05:4x S2 verdict (ruling 4). The wait is blocked because the flow's route FAILED on 11-15. Error: `[ERROR DRT-0255] Maze Route cannot find path ... Error: detail_route.tcl, 83`, `make ... 5_2_route.odb Error 2` (run_route.log 11-15 10:05 / 11:13).
  results/base holds only 3_5_place_dp.odb and 5_1_grt.odb; there is no 5_2_route.odb, so no routed DB exists to sign.
  lec_async.sh `finish` loops `until lec_async.done` with sleep 5. Its LEC unit (ot-heavy --mem 112) has never been admitted on civil-redfish, so `done` never appears.
  Running LEC cannot make these signable: there is no route, which is a hard flow failure. Current-plan V4 kits of both types are live (sle_hc2 cl3edce1b8_1124053119 and clf60c5152__pvcf529cc9_1124053155 at epyc8 abstract, items/...clf60c5152__pv0d63d22b attempt_2).
  Verdict: CANCEL after BIND-PASS: oth-ubuntu-3135343-1794696222, oth-ubuntu-3142624-1794696238, oth-ubuntu-2063722-1794715554. The cmdline check is done: each is ot-heavy-exit over s29q103S2 items/sle_hc2__cl9c4c4509__{cl3edce1b8,clf60c5152}/attempt_8 run_kit.sh/lec_async.sh.
- 05:5x FINAL cancel set (QC-FWV2-BAY answered KEEP for both fw_v2 kits; slw_fw_v2__cl8f84514c moved to KEEP, owned by QC-FWV2-BAY):
  epyc9 oth-ubuntu-819767-1795547628 (sle_fe_v2_1124081835); epyc8 oth-ubuntu-3135343-1794696222, oth-ubuntu-3142624-1794696238, oth-ubuntu-2063722-1794715554 (S2 sle_hc2 attempt_8, route failed with DRT-0255). Cancel after C1o v13 BIND-PASS, re-checking each cmdline first.

## HOLD-ECO-STALE review (FABLE-RC-QC row "ALL (hold ECO stale)"), 07:2x PST
None of the 5 has a live process: no ps line matches the kit name on its host. There is nothing to cancel.
| kit (host) | eco dir | last change (UTC) | eco_loop verdict | ECO hold plan | i-final TT WNS | FF nonport hold | can sign? |
|---|---|---|---|---|---|---|---|
| V4 private QC-ALLFIX coll_ftm_1124051759 (epyc7; archive copy on epyc2) | eco_20261124_130140_1782962 | 11-24 22:54 | PASS, "signed off after 1 ECO iteration", DRC 0 | 3 ep, worst -1.41 | +38.97 | 0.0 | YES. Already physically SIGNED in i1. Not counted: no kit_wave_stages/signed-store row (count/export gap) |
| V4 private QC-ALLFIX coll_s_1124052522 (epyc8) | eco_20261124_211939_3874698 | 11-25 00:03 | PASS, SIGNED i1, DRC 0 | 605 ep (1 padded HB4, 604 skipped), worst -0.27 | -9.88 (2 ep, inside -42) | 0.0 | Physically yes. Blocked by LEC NOT EQ class g_face_4 (QC-COLLS-LEC), not by hold |
| V2 items sle_hc1__cl22c1ff36__pve230954c (epyc2 i1; epyc9 attempt_3) | eco_20261123_092856_2078955 / eco_20261122_223653_314236 | 11-24 20:49 / 11-23 02:20 | PASS, SIGNED, DRC 0 (both) | 8 ep, worst -3.98 / -0.47 | -1.52 (1 ep) / +29.77 | 0.0 | YES, any-plan. Row SUPERSEDED (V2/V3) so not counted: re-sign/count gap |
| V2 private FAM-QC-FEFW-R3 sle_fe_v1__cl1cbb7497_1122013030 (epyc10) | eco_20261123_040953_1214866 | 11-25 07:44 (ARCHIVED to AGIdock) | PASS, SIGNED, DRC 0 | 3564 ep, worst -15.97 | +47.35 | 0.0 | YES (drv slew advisory only). Archived; check that the counter reads it |
| V2 items glue (epyc8) | eco_20261123_140713_549985 | 11-24 06:11 | EXHAUSTED "no improvement at iteration 2" | n/a | i1 -61.73 (81 ep), i2 -98.25 (71 ep) | 0.0 | NO by ECO: setup beyond -42 and worsening. Structural setup fix (glue rows, C1p QC-GLUE); not a hold problem |
Finding for QC-HOLD-STRUCT: none of the 5 is a live hold failure. In all 5, FF non-port/core hold is 0.0 after ECO. Four are SIGNED in eco_loop and only missing count/LEC. Glue is a TT setup miss.
