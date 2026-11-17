# FABLE-CLOSURE-STRATEGY 2026-11-17 15:20 PST (1520): delta on 13:20

Reviewer: FABLE-CLOSURE-STRATEGY-1520 (Fable). Read-only, no jobs launched. Technical PD only. HBM parked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0 (port hold advisory), die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal, not measured.

## 0. Headline

1. **No svc core is routing, and sml has no -96 ps (V).** Five of the six split-core builds exited 1 at CTS between 14:16 and 14:55 on one recipe error: `cts.tcl, 83 OT_HOLD_STRUCTURAL: synchronized FF scene BC unavailable; enable multi-mode FF timing before hold repair`. The sixth (smc, intel1) is still waiting for admission. Post-CTS setup: sml, smd, smr `RSZ-0098 No setup violations found`; hslice -25.87 repaired to +0.19; merge_x -103.99 on 16 ends, all at output port `of_[10]`, not repaired. The only core timing problem is an unregistered output on merge_x.
2. **The first placed svc timing (hi3 flat, `4_cts_final.rpt`, 14:15) shows the structural problems are in the shell, not in the cores (V).** Worst setup -3404.03, clk period_min 4237 ps. Four separate causes, section 2 lever 4. The largest is new and has a one-line fix: the 1,024 `ot_s81c_hcore_load_stage.out_w` flops of tiles t_0, t_1, t_2 were merged into tile t_3's (netlist count 0 / 0 / 0 / 1024), so one register bank drives the hcores of all four tiles through 39 buffers and 2,448 ps of wire.
3. **The serdes rail defect is not S81-only: HEAD `hd_serdes` has it (V).** Rail check in report mode on the hd_serdes NF13a floorplan: 3,047 of 5,672 rows without a rail. hd_serdes sd9f was signed today from the same generator. 17 other sampled families pass, but the sample took one kit per name prefix and missed every other PHY type (QC `coll_ucie`, signed 08:20, is one).
4. **QC and KV have no dominant measured technical failure class, because nothing has routed on their current trees.** QC: 0 rows on N1B have reached CTS. KV: 12 HG5 rows are placed, none routed. The placed rows do share one advisory signature that the serdes and svc measurements say matters: taps far over the sink size that lands at the insertion target.
5. **H17 routed TT is still not measured.** The route-only rerun was at 50 % of iteration 0 (58,030 violations) at 15:15. The census crashed twice in OpenSTA.

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| svc core builds | epyc2 `/srv/opentallas-scratch3/claude/s81-svc-split/build/{sml,hslice,smr}_h16/{STATUS,flow.log,sta.log}`, epyc8 same dir `{mergex,smd}_h16`, `*.exit` | all five `EXIT=1`, `flow_rc=1`, stop at `do-4_1_cts` with the `OT_HOLD_STRUCTURAL ... scene BC unavailable` error. Recipe line in the same log: `OT_ORFS_CORNER=TC (tt_overlay v2) ... hold corners WC,BC`. No file newer than 14:56 in any build dir; intel1 has only the queued `route_core.sh smc` |
| svc core CTS numbers | same `flow.log` | sml: util 51.8 %, 79,311 cells, 140 input pin flops, insertion 205-262 ps, no setup violation. smr 45.2 %, smd 40.5 %, none. hslice: `ko_key[413]` -25.874 / 56 ends -> +0.186. merge_x: `of_[10]` WNS -103.988, TNS -668.1, 16 ends, 2 buffers + 55 resizes, `RSZ-0062 Unable to repair all setup violations`. Link budget on all: T 770, in / out max 487 |
| hi3 flat CTS final | epyc8 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc/f2s3_mpl8/svc_hi_dsdv_svc_rs__t3/gen/svc_hi_dsdv_svc_rs__t3/run/reports/asap7/dp_svc_hi_dsdv_svc_rs__t3/base/4_cts_final.rpt` | wns max -3404.03, tns -185,676,272, clk period_min 4237.03. Clock clk setup skew 1944.37 = 1878.42 at `...g_t_3_..._u_hc_u_load_stage.out_w[969]/CLK` against 65.94 at hcore `...g_t_0_..._g_h_12_u_c/clk`, CRPR 0. Groups (max): asynchronous -3355.61, path delay -877.46, fclk_in_attn_i2 -437.99, fclk_in_attnh_i0 -176.06, vclk -636.24. Groups (min): clk -1620.78, vclk -292.66, attnh_i0 -284.13 |
| hi3 worst clk path | same report, lines 1599-1871 | launch `g_t_3 ... load_stage.out_w[121]` on `clk_t34`, CLK at 1877.10 through 44 clock buffer levels; data = 1 INVx4 + 39 buffers (BUFx6f / BUFx16f), no logic, 1937.52 -> 4385.83; end pin `g_t_0 ... g_h_0_u_c/ld_w[121]` (slew 152 ps); capture hcore `clk` at 767.06, 0.06 ps from tap pin `clk_t10`; setup 214.74 |
| hi3 register merge | same kit `run/results/.../1_2_yosys.v`, `config.mk` | `load_stage.out_w[*]` flops per tile: t_0 0, t_1 0, t_2 0, t_3 1024. `OT_KEEP_WIRES` lists `ot_s81c_hcore_load_stage:bad_w2v`, `:out_mode`, `:out_v` and not `:out_w`. `SYNTH_ARGS = -noshare`, `SYNTH_HIERARCHICAL = 0` |
| hi3 CTS tap load | same kit `run/logs/.../4_1_cts.tmp.log` line 189-194 | `OT_TAP_PAIR registers on taps 605921, taps 53 ... taps above cap 1500 at start 34 ... groups moved 0 clock pins moved 0 cross-tap short pairs 11209` |
| rail sample | intel2 `~/fable-fix-s81-serdes2/rail-sample.out`; list epyc9 `.../fable-fix-s81-serdes2/drtx/rail_sample/list.txt` | 19 floorplans. FAIL: `s81/serdes` 2000 of 6656, `s81_head/hd` 3047 of 5672 (= `hd_serdes` attempt_8, event NF13a; first rows y 399.87, x 4.32-2881.44). PASS (0 bad): HBM PHY_NC, PHY_NW, q, vsN1, vsN4; QC cbf, cbn, cbx, coll (= coll_core), sle_su; KV kv3_io_ft; S81 col_h10, col_h9, col_h9_r0, ot_s81sl; HEAD hd_spn_wshim, hd_turn |
| serdes PG, H17 | intel2 `~/fable-fix-s81-serdes2/{pgchk3-E2-VDD.out, H17-route-1117-r2.out, ttsk-H17-r2.out}`; epyc9 H17 kit `5_2_route.tmp.log`, `grt_policy/tt/pair_skew.tsv` | E2 (notch v2) still `PSM-0069` on VDD (rail defect present, as expected). H17 r2 in iteration 0. Census: `rc 139`, `TSK wns -34.42`, 2 ends, then signal 11. pair_skew: 51,361 regs, 546,030 pairs, 10,419 inter-clock, max_worst 509.42 |
| QC wave rows | intel2 `autopilot/kit_wave_state.json` 15:10 | No item on event `s29q103S4Q9N1B` yet. L2: 63 rows = 32 placed (3 route-held), 26 kit_rtl, 2 gen, 1 src_manifest, 1 MPL-0034, 1 cancelled. Auto-geom on the 32 placed: `r2r` 32, `pin_reg_max` 32, `fill` 29, `relay_collapse` 25, `col_v` 24, `clock_tap_sinks` 17, `channel_v` 12. `grt=ok(0)` where read |
| KV wave rows | same file | HG5: 12 placed (enqueued), kv3_hroot band FAIL, kv3_hub_Wi prov_views, kv3_hub_C stopped, kv3_hub_Wo placing. Auto-geom on the 12: `r2r` 12 (count 14 to 16,352), `col_v` 12, `relay_collapse` 12, `clock_tap_sinks` 10, `channel_h` 9, `clock_on_macro` 7, `clock_reach` 4, `grt` 3. kv3_hub_C attempt 2 repair table at place: WNS -2480.6, 14,726 ends, endpoint `u_kvs_attn.u_core.u_attn_face.res_t[0]/SETN` (reset recovery, before the reset tree) |
| failure_breakdown | intel2 `tools/failure_breakdown.py` 15:10 | technical rows only. S81: macro placement 2, congestion 1 (phy__t1), place error 1 (serdes__t3), hold after CTS 1 (serdes__t4), route held 14. QC: macro placement 1, route held 4. KV: CLAND ring band 1. HEAD: none |

Not opened: D6z / D7z builds, pg3 and ir1 sign-off reports, the N1B gate records, the D21 gate result (client log shows exit 0 only), rs8b, the lep_pair hold ECO, the sd9f signed DB, hub_Wi stat, c1x_C t7 / t9 logs, phy__t1.

## 2. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D6z applied, col released with the per-kit GRT frame read | 78 col types now, 203 in the family | S81-DIE-R3, S81-TYPES-R3 |
| 2 | QC | one pilot per family to sign-off on N1B, with per-tap insertion read at CTS | 117 open types | QC-TYPES-R3, FABLE-FIX-QC-N |
| 3 | KV | D21 applied; D22 = hub_C rows + hub_Wi host clusters; reset and tap read on the first routed kit | 50 open types | FABLE-FIX-KV-HG |
| 4 | S81 | svc: keep `load_stage:out_w`, hcore clock, ring macros, core recipe | the svc family (lo7, hi3, t6, pvso; count not read) | FABLE-FIX-S81-SVC2, S81-SVC-SPLIT |
| 5 | S81, HEAD, QC, KV | PHY-region rows: rail check on every PHY type, signed ones included | 11 S81 serdes + hd_serdes + unsampled PHY types | FABLE-FIX-S81-SERDES2, HEAD-TYPES-R4 |
| 6 | all | tap size: print per-tap insertion at CTS; split taps that pair with others | S81 serdes (clk_t42), svc shell, first QC / KV kits | FABLE-FIX-S81-SERDES2, S81-DIE-R3, WAVE-FLOW-R2 |
| 7 | HEAD | rs8b gate, lep_pair 7-end hold ECO | hd_lep0N, hd_mesh | HEAD-PLAN-R4, HEAD-TYPES-R4 |
| 8 | S81 | strip: t22 to GRT on D7z | 20 flagged, then 75 leaf types | S81-DIE-R3, S81-TYPES-R3 |

### Lever 1. S81 col (78 now)

Evidence. D6x / D7x bind failed on two tap-legality rows (kv_leaf__t1 tap `clk_t29` under the moved SRAM; t51 shared tap `clk_t19` 0.020 um off its first landing); fitter now checks tap legality, TAPBAD 0; D6z apply about 18:15 (R, S81-DIE-R3 14:40-14:42). pg3 signed TT -39.22 (R). ir1 not signed, TT -181.27, FF hold -58.3, on the old tree without the col knobs (R).
Fix. Unchanged from 13:20: per-kit `OT_GRT_FRAMES` read, hold a member under -30. Add:
1. ir1 is not evidence against col_h9_r1. It is the only routed r1 number, so the first r1 kit on the ordered-rows tree goes to sign-off as a pilot before the r1 members.
2. kv_leaf__t3 (MPL-0041) is the same SRAM pair D6z moves: first D6z kit list must include t1 and t3 place.
3. c1x_C t7 / t9 `GRTM edge_outline` is plan geometry and is not released by D6z or by the dup-bb merge. It needs an owner row today (S81-DIE-R3).

### Lever 2. QC (117 types)

Is there a dominant technical class? **No measured one.** N1B was applied at 14:40 (R); the wave state holds no N1B row at 15:10 (V). On L2, 0 rows failed at CTS, GRT, route or timing; all 31 failures are tree or kit input classes, plus one MPL-0034 (V).
What the placed L2 rows say (V, advisory metrics at 3_place):
- `clock_tap_sinks` fails on 17 of 32: coll_core 20,901; slw_hc0 5,538; slw_hc3 4,248; sle_hc2 3,722; slw_hc2 3,286; slw_hc1 2,470; slw_fw_v1 1,948. Over all QC rows with a value, 87 of 130 are over 1,650 and 41 over 4,000.
- `r2r` fails on 32 of 32 (pairs over the distance limit: 4 to 5,530).
- No congestion signal: `grt=ok(0)`, fill 0.03 to 0.12.
So the QC risk is clock insertion spread and long register pairs, not routability. It is a prediction until a kit routes.
Fix.
1. QC-TYPES-R3: the three cb pilots plus one kit per family, straight to sign-off. At CTS read the per-tap insertion (lever 6). `hc0` (351k cells, tap 5,538) and `coll_core` (tap 20,901) first: they are the largest taps.
2. FABLE-FIX-QC-N: the cb kit gen log says `TAP_WINDOW FALLBACK for cbn_q01__clab6e67f2 (no clock.tap_window.per_port_ps entry, flat 482.9 ps)` (R). A flat window on the type that carries the 68 lockup pads: check the four `tap[0]` pins on the pilot's CTS before route, not after.
3. N2B after the pilots launch: st_a move (2 types), `HI_PAD` hold (R, bind 0 errors).
4. cbn_q00 core-outside: fixed in N1B by the NB slot delta (census 0, R). Confirm on the cbn_q00__cldbcda913 kit place.

### Lever 3. KV (50 types)

Is there a dominant technical class? **Not a failure class; one shared risk signature.** 12 HG5 rows are placed and none routed (V).
- `clock_tap_sinks` fails on 10 of 12; over all KV rows 47 of 52 are over 1,650, 32 over 4,000 (kv3_hub_Wo 41,359; pv_v4 28,043; hg_v1p6 20,433).
- `r2r_count`: pc_v1 16,249 and 16,352; pc_v3 10,139; pv_v12 8,030; pc 7,721; pv_v7 6,860; pv_v1 5,535; sys_c 4,407. `r2r` up to 2,697 um. These are register pairs with no relay between them at type level.
- `clock_on_macro` 7 of 12, `clock_reach` 4 of 12 (pv_v12 270 um).
- Reset: kv3_hub_C at place reads -2,480 on 14,726 SETN ends before its reset tree (V).
Fix.
1. FABLE-FIX-KV-HG: apply D21 on PASS. First PC kit (`kv3_pc_v1__cl23f6a148`) and first PV kit (`kv3_pv_v12`) to sign-off without waiting for volume: they have the largest pair counts. Read at CTS: per-tap insertion. Read at GRT: frame TT split by class (station pairs against the rest). If the 16k pairs show as one class under -42, the fix is relay rows in the plan (D22), not a kit retry.
2. D22 hub_C: the 17 ring rows + pvfin pair (R, rows written against D21; placement cleared against hard-core halos only). G0 must place-check them against ft stations, taps and reset sites. After the split, re-read the SETN recovery on the shell: the 14,726 ends must sit behind per-region relays.
3. D22 hub_Wi: `u_host` is 902,681 flat because the 22 `qkd_hr_*` clusters exist only through the opt-in `kv_core_rtl.py --hr-wrappers --split` step and their rows have no lef / lib (R, FABLE-FIX-KV-HG 13:28). The split is a kit_rtl wiring step plus views for 13 modules. Do not launch any Wi shell before the hierarchical count exists (unchanged).
4. kv3_hroot: v6 moves the one zero-band stage 7.99 um (R). Next smallest band is kv3_pv_v6n raw:o:4 with 1.17 um2 free for about 0.9: watch it on the first PV kit.

### Lever 4. S81 svc family

Do the split outlines and the -96 ps point to a structural timing problem? **The cores do not. The shell does, in four places, all measured on hi3 flat at CTS (V).**

| # | class | number | root cause | fix |
|---|---|---|---|---|
| a | hcore load bus | -3404.03; data 2,448 ps, 39 buffers, 0 logic | `load_stage.out_w` flops of four tiles merged into one bank (0 / 0 / 0 / 1024); `out_w` missing from `OT_KEEP_WIRES` | add `ot_s81c_hcore_load_stage:out_w` to the keep list in the svc generator; check `out_grp` / `out_bank` style outputs of the same module with the same grep; each tile's load stage placed with its 16 hcores |
| b | clock | setup skew 1944.37; hold (min) -1620.78 hcore -> `r_iy[511]` | 605,921 registers on 53 taps (11.4k per tap, 34 taps over the 1,500 cap), 44 buffer levels, 1,877 ps insertion; hcore `clk` pins sit on the tap pin with no tree | after the split the shell keeps about 0.6M cells: size taps to <= about 1,650 sinks (lever 6); give the 64 hcores their own tap group and delay it to the shell insertion (the hcore view must state its internal insertion) |
| c | reset | recovery -3355.61, arrival 4,238 ps | one source flop fans out through a buffer chain to the merge flops | goes away for sinks inside cores (own reset entry register); the shell needs per-region relays, checked on the shell CTS |
| d | landing rings | path delay -877.46 (`u_cland_attn_i2/u_ring.ctl_w[0]` -> `rv`, max_delay 416.5); ring inputs -437.99 / -176.06; outputs vclk -636.24 | soft rings spread by placement. The handoff's "+178.53 MET, not a long cone" was read on the unplaced floorplan | make the 14 landing rings hard ring macros in the first shell, not as a later cut (KV masters sign at +75 to +146) |

Cores (V): no data-cone problem. merge_x needs output registers on `of_` (16 ends at -104 against a 487 ps port budget; +1 cycle, latency row). hslice `ko_key` closes by sizing.
Fix order.
1. S81-SVC-SPLIT: relaunch the five cores with the hold scene fixed. The recipe sets hold corners `WC,BC` under the TT overlay and the BC scene is not loaded. Use the kit route env that the signed S81-SVCRS-3 providers used; this is the recipe, not the design.
2. FABLE-FIX-S81-SVC2: item (a) into the generator now. It applies to lo7 and to the split shell equally, and it is one keep-list entry.
3. FABLE-FIX-S81-SVC2: stop treating hi3 flat as a data point to wait for. Its CTS report already answers the open question: there is no single -2.57 ns data cone; there are (a) to (d). The run can go on to GRT for the congestion map only.
4. Outline: core utilisation at +12.5 % area is 40 to 52 % at CTS. No outline change is justified by timing. Fix the outline from routed cores.

### Lever 5. PHY-region rows (S81 serdes 11, HEAD hd_serdes, others unsampled)

Does the rail fix generalise? **Yes, to HEAD at least (V).** `hd_serdes` NF13a floorplan: 3,047 of 5,672 rows without rails. The S81 number on the wave kit is 2,000 of 6,656 (2,046 of 6,664 on H17).
Root cause (R, FABLE-FIX-S81-SERDES2 14:47): rows that overlap a PHY supply region get no CORE followpin rails from pdngen; tapcell cuts rows at macros only. Fix on READY branch `claude/s81-serdes-pad-pg-rails-1117` @c8ce59b7: rows replaced by their pieces outside the region before tapcell (F2: 6,726 rows, 0 bad), and the rail check as the last POST_PDN step of every kit.
Fix.
1. HEAD-TYPES-R4: run `pg_rail_check.tcl` in report mode on the **signed sd9f** `6_final.odb` (not the NF13a floorplan). If rows are bad, count the instances on them that are not tap cells. S81 had about 480 logic cells incl. 56 flops on 2,108 rows. Unpowered flops are a functional defect, so this is not an advisory PG item; hd_serdes then needs a rebuild from the fixed generator and sd9f's ECO replayed with `capskew_eco_run.py` (replay proven, R).
2. FABLE-FIX-S81-SERDES2: the sample missed PHY types because it took one kit per prefix. Run the check on every type whose plan has a PHY supply region or a macro_pin pad: QC `coll_ucie` (signed 08:20) and the serdes / UCIe face types, KV io types with `qkd_hr_phy_adp`, HBM PHY_NE. List from the plan (`phy_pg_pdn` users), not from kit names.
3. After merge the check fails kits at floorplan. Before that, the same check in report mode on the three first-wave floorplans of QC N1B and KV D21 costs minutes.
4. Serdes placement form: the DRC-0 / TT -27 result is the hand lineage H3p -> H5 -> H17 (about 40 stage files, density 0.30) and gen_phys cannot reproduce it (R, 15:09). The other 10 types cannot go through the wave until it is ported. Port first (option 1); the rail fix alone releases nothing.

### Lever 6. Tap size and per-tap insertion (all dies)

Evidence.
- S81 serdes H17 (R, 15:09): taps of 716 to 1,649 sinks land at 247 to 327 ps for a 250 target; `clk_t42` with 6,502 sinks lands at 554 (538-715). Result: 509 ps pair skew, the worst `clk` setup path.
- S81 svc hi3 (V): 11.4k registers per tap, 1,877 ps insertion, 1,944 ps skew against macro pins.
- Wave rows with a tap over 1,650 sinks (V): QC 87 of 130, KV 47 of 52, S81 278 of 332, HEAD 7 of 27.
Limit of the evidence: HEAD has signed types with large taps (hd_host 22,847 on an older event). A large tap fails only where its registers pair with registers on another tap or on a macro clock pin. The count alone is not a gate.
Fix (P).
1. WAVE-FLOW-R2: print per-tap mean / min / max insertion and the cross-tap pair count at CTS in every kit (the serdes lane reads it from the CTS log already; `OT_TAP_PAIR` prints the pair count). Advisory line, no gate.
2. Plan owners: where a tap is over 300 ps TT and has cross-tap pairs, split it in the plan to <= about 1,650 sinks per tap. First: S81 serdes `clk_t42` into four taps (R, numbers above), with S81-DIE-R3.
3. Not a new rule for signed types and not a re-floor of taps without cross-tap pairs.

### Lever 7. HEAD (2 types)

rs8b (rs7 + c3 stage rects, r597 tools) admitted on epyc9 after a lost first launch (R). lep_pair KCRED 28: LEC equivalent, DRC 0, TT +7.68, internal hold -3.33 on 7 ends; `hold_eco_internal_run.py` running (R). Both are execution. Technical read still owed from 13:20: hd_lep0N first to GRT with no early stop, per-layer overflow in y 665-846; c3 leaves 367 of 59,089 nets unassigned in x 880-1160 and 1230-1472 (R), so read those two x windows first.

### Lever 8. S81 strip

Unchanged: t22 to GRT from D7z (apply about 18:45, R). No new number since 11:20.

## 3. Stop list (changes; the 13:20 list otherwise stands)

1. svc: relaunching the cores with the same TC hold recipe; any pipeline or outline change on sml / smd / smr (they meet at CTS); a shell kit without `load_stage:out_w` kept; waiting for hi3 sign-off; quoting the unplaced +178.53 ring number.
2. Serdes: sign-off or export of any PHY-region type before its rail check; rail ECO on H17; generating the other 10 from gen_phys before the H form is ported.
3. HEAD: counting hd_serdes sd9f as clean before the rail check on its signed DB.
4. QC / KV: volume routing of a family before its first kit shows per-tap insertion and GRT frame TT; calling the kit_rtl and prov_views rows design failures; a hub_Wi shell before the host clusters are instances.
5. All: a tap-sink gate from the advisory count alone; a family-wide GRT derate (unchanged).
6. S81 col: reading ir1 (-181) as a verdict on col_h9_r1.

## 4. Corrections to the 13:20 report and to the 15:05 state

1. **"svc split cores routing; sml at CTS about -96 ps" does not match the disk.** All five launched cores are dead at CTS on a recipe error; sml has no setup violation. The nearest number is merge_x -103.99 on an output port.
2. **13:20 lever 5 item 1 called the serdes west-edge PG failure an advisory item outside the gates.** It is rows without rails under logic and flops. That was wrong; it also exists on HEAD.
3. **13:20 section 6 left "whether other types share it" unchecked.** One does (hd_serdes); the sample that says the rest are clean did not cover the PHY types.
4. **13:20 lever 2 said QC's 117 are "unmeasured".** Still true after the N1B apply; the placed-row advisories are the only data and they point at clock taps and register distance, not congestion.

## 5. Not checked

- Whether the signed sd9f DB has the bad rows: I read the NF13a attempt_8 floorplan only.
- The svc lo7 netlist for the same `out_w` merge (same generator and keep list, so expected; hi3 only was counted).
- Whether `ot_s81c_hcore` has internal clock insertion; lever 4 (b) depends on it.
- The distance limit behind `r2r` and the exact meaning of `clock_tap_sinks` (I read it as the largest tap).
- The exact hold-scene setting that makes the core recipe pass.
- D21 gate verdict, D6z progress, rs8b result, H17 routed TT.
