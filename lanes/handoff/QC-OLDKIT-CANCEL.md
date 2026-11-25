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

## Log
- 05:2x census + classification. Waiter armed for "BIND-PASS C1o v13 aa3a14fb7484" in lanes/posts/QC-C1O-COMPOSE.md.
