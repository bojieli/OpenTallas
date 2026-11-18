# FABLE-CLOSURE-STRATEGY 2026-11-18 13:20 PST (1320): delta on 09:30

Reviewer: FABLE-CLOSURE-STRATEGY-1320. Read-only: no jobs launched, nothing killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0.
Marking: **V** = I opened the file or log this round (13:10 to 13:20 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate. **I** = inferred from V data.

Signed (V, failure_breakdown 13:10): S81 43/394, HEAD 24/26, QC 26/130, KV 6/56.
Method (V): the eight lanes' posts since 09:30; one scan of the 239 live `ot-jobs/*-route-*/work` dirs on the six build hosts; then the sign-off STA logs, CTS reports and congestion reports named in section 2.

## 0. Headline

1. **The first routed QC N3 kit fails internal FF hold, and every QC kit in flight stops its hold repair at the same point (V).** sle_hc0__cl929603c0__cl38badc56: detailed route 0 violations, routed TT -29.85, but routed FF internal hold -21.57 on 152 ends (TT corner -16.58 on 13). The GRT hold repair had stopped at +6.56 against an asked margin of 40 (`margin chase stalled, stop`). The route cost 28 ps of hold and 43 ps of TT setup (GRT estimate +12.81).
2. **D8e r6 is the one event that carries four S81 fixes (about 290 types), and its tools need three commits that were made after the plan was composed (R + I).** XR HI rows (77 leaf / kv_leaf), col_h9_r1 frame stations (60), 5 um halos (216 col types), serdes star + boot path (11). A 5 um halo without `macro_halo_carve` stops every kit at 3_5 (DPL-0004), as it did on QC st_a today.
3. **col_h9_r1 is being rebuilt unchanged (V).** Five more kits ended `GRT-0116` between 10:10 and 11:05, and at least 9 new kits are in place / CTS with all 354 `frame_int` station sites still at y 1226.88. The allow-congestion test is not a cheap path: 3.7 h in, it has not reached detailed route.
4. **KV hgi_v1 closes setup, and its next blocker is already visible (V).** Kit k3 at GRT iteration 5: overflow 44,172 in 17,057 gcells, all in the west band x 0 to 200, y 400 to 1200, on the `u_hst2_t1.u_reg.ti_b` and `cland_ft2_i` buses. The base kits had the same band (0930). The 172 hold ends at -102 are all `port_in`, so they do not block.
5. **col_h10_r1 (12 types) is held by a single-bit path, not by a family problem (V).** wns -138.57 with tns -252: `u_lpad_frame_int_i1.q[819]` -> 9 wire buffers -> `u_d1_11_Y.q`, 792 ps of data. Setup repair gains 0.
6. **S81 routed FF hold is not a problem (V).** The negative FF numbers on today's S81 exports are port-start paths: col_h9_r2 pilot `STD_MIN_NONPORT n 0` (340 port ends at -61.39), slice_station t28 n 0. The col pilot is signed at TT -38.29. This closes 0930 stop-list item 8.

## 1. Levers ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D8e r6 apply with tools at or after de34662bfb5, bd76ec2856c, dc9b82ef5b5 | leaf 77, col_h9_r1 60, col halo 216, serdes 11 | S81-DIE-R3 |
| 2 | QC (HEAD next) | Hold and setup repair at GRT must cover the measured route loss (hold 28 ps, TT 31 to 43 ps) | about 90 QC rows in flight; hd_mesh | QC-TYPES-R3, FABLE-FIX-HEAD-MESH |
| 3 | S81 | col_h9_r1: stop unchanged rebuilds; frame rows come with lever 1 | col_h9_r1 60 | S81-COL-FLOW-1118, S81-DIE-R3 |
| 4 | KV | D23h2 apply (relay keys + reset tail); west-band rows for hg / hgi in D24; e0 re-harden for the kt stages | hg / hgi 17, then pv 16 | KV-D23-COMPOSE, FABLE-FIX-KV-HG, KV-KT-E0 |
| 5 | S81 | col_h10_r1 / r2: site the `u_d1_*_Y` single-bit flops at their landing-pad bit | col_h10_r1 12, r2 12 (r2 not read) | S81-GEOM-OPUS |
| 6 | QC | Structural rows: cbx_q10 strap pins, stm_v3 so_e pins, hc1 wep copies, st_a tail hops over 380 um | cbx_q10 4, stm 1 to 3, hc1 1, st_a 11 | QC-PLAN-R3, QC-TYPES-R3, FABLE-FIX-QC-STA |
| 7 | S81 | Serdes: H21 to sign-off as evidence; countable kits from D8e with the star row | serdes 11 | FABLE-FIX-S81-SERDES |

### Lever 1. D8e r6: one event, four fixes, three tool commits

**Evidence.**
- R (S81-DIE-R3 12:39): r5 was red on one class, 77 `LF_CS_DEPTH hi` errors. XR adds one per-lane HI stage in `ot_s81sl_vp`, so the bound depth is plan + 1 on the 77 types that had no XR. r6 plan df7446e48ba9 appends one HI reg per lane (11,214 rows). Prechecks with tree tools 8efd33fb: 0 errors.
- V: epyc8 `s81-die-r3-e8/d8e/r6`: `elab.log` 1.0 MB and still written at 13:14, `bind.log` empty. No result yet.
- R (S81-GEOM-OPUS 12:33): the plan carries the col_h9_r1 `frame_int_o0 / i0` stations 27 to 42 um inside the north edge, and `halo_um 5` on 1,368 sstn / cfifo cores in 216 col types. The halo needs main 8958d3e8a4e.
- R (FABLE-FIX-QC-STA 12:57): on QC st_a a 4.32 um halo put 1,344 endcaps and 152 tapcells inside the blockage ring, and both kits stopped at 3_5 with `DPL-0004 (1496)`. Fix on main de34662bfb5 (`macro_halo_carve.tcl`), proven on k4.
- R (FABLE-FIX-S81-SERDES 12:35, 12:43): star key on main bd76ec2856c; boot path export on main dc9b82ef5b5.

**Root cause of the risk (I).** The prechecks ran with tree tools 8efd33fb. Nothing in the posts says that the r6 tree carries 8958d3e8a4e or de34662bfb5. A 5 um halo is wider than the 2.05 um row cut, so 216 col types would repeat the st_a stop.

**Fix (S81-DIE-R3).**
1. Before the apply, check that the D8e tools hold all of: 8958d3e8a4e (HALO-1), de34662bfb5 (halo carve), bd76ec2856c (star), dc9b82ef5b5 (boot path), 922c27887ac (TT setup repair). If the tree is older, refresh the tools; do not drop the halo rows.
2. First kits to read after the apply, one each:
   - a leaf with XR: `OT_VPW_BANK placed N` (about 1,219 = XR at the bank) and post-CTS TT;
   - col_h9_r1: GRT residual in x 660 to 780, y 1200 to 1227;
   - col_h9_r0_p6 with halo: passes 3_5, then M5 shorts at the cf macro west end (was 21 of 25);
   - serdes__t13: `OT_RCK_STAR` lines and the boot recovery endpoint.
3. XR-MID (58 far types) stays the delta after this event.

### Lever 2. Repair at GRT must cover the route loss

**Evidence (V, epyc9 `ot-jobs/sle_hc0__cl929603c0__cl38badc56-route-*/work`).**
- `run_route.log`: `OT_HOLD_GUARD_GRT start: hold ws -24.53 viol 140, margin 40`; chunk 1 +4.69 (1,110 buffers, 3,269 s); chunk 2 +6.15 (306 buffers); chunk 3 +6.56 (202 buffers); `hold met (ws >= 0), margin chase stalled, stop`.
- Same log: `OT_TT_SETUP_REPAIR ... wns -84.95 -> 12.81` at GRT.
- `signoff/tt/sta.log`: `STD_WNS_MAX -29.85` (105 ends), `STD_MIN_NONPORT n 13 wns -16.58`.
- `signoff/ff/sta.log`: `STD_MIN_NONPORT n 152 wns -21.57 core_n 152`.
- Worst hold path: `u_u_xl0_0.wd[394]` (tap clk_t90, source latency -9.6, insertion 171 ps) -> INV -> buffer -> OA21 -> `u_u_xl0_0.g_t[1].g_e[24].m[10]` (tap clk_t104, source latency +20.6, insertion 250 ps), plus 25 ps uncertainty. The kit has `OT_TAP_PAIR_AFFINITY = 1`, and the pair is still cut.
- Sister kit cl4baa7c9c: GRT hold +6.63, sign-off STA still running (SDC-level FF min -45.53; the non-port line is not out).
- R: hc1 routed -59.5 from a GRT estimate of -28.6 (31 ps). Every finished QC kit ends its GRT hold repair at +5.0 to +8.2 (FABLE-PD-QC-1240).
- R (QC-TYPES-R3 12:49): main b5bdd3347e1 cuts the first hold chunk to 200 buffers. The 10 ps pad is not applied.

**Root cause.** The guard treats "ws >= 0 and gain under 1 ps per chunk" as done, and the chunk cap shrinks (1,110 -> 306 -> 202), so the gain per chunk falls below 1 ps although only 1,618 buffers were spent. The repair therefore ends 34 ps short of its own margin, and the route takes 28 ps. With a 200-buffer first chunk the stop comes earlier.

**Fix.**
1. QC-TYPES-R3, `hold_guard_grt.tcl`: apply the stall stop only once ws >= 30 ps (the measured loss), and keep the chunk cap at 1,000 or more until then. Do not apply the 10 ps pad. This is the check the 12:40 review asked for, and it came out negative.
2. QC-TYPES-R3, the two routed hc0 kits: post-route hold ECO on the 152 ends, with the TT corner loaded so setup is seen. Buffer the `wd` branch, not the `m` D pin: the same endpoint is the TT-critical `wep` enable path (I: that is why the hc1 ECO cost 82 ps of setup).
3. Structural, P: the `wd -> m` bank pairs need the HEAD rule (`OT_TAP_PAIR_MACRO` form: the register array follows the tap of its `wd` flops). On hd_mesh it cut internal hold ends 11,163 -> 5,251 and hold buffers about 35,000 -> 9,629 (R).
4. TT side: a kit whose GRT TT estimate is under 0 will land outside -42 after a 31 to 43 ps loss. FABLE-FIX-HEAD-MESH: mesh_pa is at GRT TT -32.92 (V), so expect about -65 to -75 routed (P). Keep mesh_w1 alive and prepare a routed TT repair on the mesh_pa DB now.

### Lever 3. col_h9_r1

**Evidence (V).**
- `GRT-0116` again on epyc9 pv2f96c04f, pv4593e8e5, pv5ffbfb8b and epyc10 pvd9381c1d, pvee46d7b8 (logs last written 10:10 to 11:05).
- epyc8 pv15cef3f7 (launched after 09:30, in CTS): `istations.tcl` has 354 sites at y 1226.88. TT -277.6 before repair.
- Allow-congestion test (epyc7 `lanes/s81-col-flow-1118-grtac`): GRT 6,300 s, `GRT-0115`; then `OT_MAXWIRE` at 100 um added 79,494 cells (257,455 -> 336,949) in 5,642 s; hold repair is flat at -64.39 with 183 ends at `u_bn6/e_r0[1]`. Not in detailed route at 13:15.
- S81-COL-FLOW-1118 has not posted since 09:30.

**Fix.** S81-COL-FLOW-1118: no further col_h9_r1 builds on the d8t plan; the frame rows arrive with lever 1. Read the test's DRT only if it gets there; do not copy the hook to other kits. One read is owed: whether `OT_MAXWIRE` adds 30 % cells on a normal col_h9_r2 kit too, or only after congested routing (hc0 at 120 um: +2,510 cells in 118 s).

### Lever 4. KV

**Evidence.**
- R: k3 (hgi_v1 with relay keys, reset tail, 28 x 2 parent kt stages) TT +0.43 after CTS; tap spread 96 ps.
- V, k3 `run_route.log`: `OT_PREGRT_FF_HOLD class after port_in 172 ws -101.93 same_tap 0 cross_tap 0`; `cross-tap guard not applied (no tap window lines in the kit SDC)`.
- V, k3 `congestion-5.rpt`: 17,057 of the 20,000 listed gcells lie in x 0 to 200, y 400 to 1200 (H 8,614, V 8,443), overflow 44,172; peak column x 80 to 140. Top nets: `u_hst2_t1.u_reg.ti_b[*]`, `cland_ft2_i[*]`. 2,759 pins sit on the west face. GRT was at extra iteration 9 of 30.
- R (KV-D23-COMPOSE 13:00): D23f applied without the keys; D23h2 (keys + reset rsync / rtail) sealed and green; fix #2 needs e0 RTL + re-harden + calendar +2 (NEEDS-LANE KV-KT-E0).

**Root cause (I).** The hst2_t1 bus and the ft2 landing bus share a 200 um band behind the west face, and the relay stations are FIRM on source-to-sink lines inside it. Both directions overflow equally, so it is local density, not one bundle.

**Fix.**
1. KV-D23-COMPOSE: apply D23h2 now. It closes setup on 17 types apart from the kt class.
2. FABLE-FIX-KV-HG: post the k3 GRT end (residual and box). If it ends with `GRT-0116` or a residual over about 500, write D24 rows that move the hst2_t1 relay line out of x 80 to 140 and stagger it against the ft2 landing rows (P, 0 cycles).
3. KV-KT-E0: start the e0 source change today; it is the long pole (re-harden at the frozen 216 x 216 outline).

### Lever 5. col_h10_r1 / r2

**Evidence (V, epyc9 pv86f5e3b9 `4_cts_final.rpt`).** wns -138.57, tns -251.99, so 2 to 4 ends. Path: `u_lpad_frame_int_i1.q[819]` (tap clk_t12, CLK 339 ps) -> INV -> 9 buffers -> `u_d1_11_Y.q` D at 1,220.5 (tap clk_t22, CLK 307 ps). `OT_TT_SETUP_REPAIR cells 8 added; wns -145.99 -> -145.99`. The first report path (reset recovery, `u_d11_11_Y_r119`) is met at +240.8. Tap spread 79 ps.

**Root cause (I).** `u_d1_11_Y` is a single-bit delay flop with no site row. Global placement puts it at its loads, about 1 mm from the landing-pad bit (P from 355 ps of wire delay).

**Fix (S81-GEOM-OPUS).** A relay-site row that puts each `u_d1_*_Y` flop within 100 um of its landing-pad bit, or one station on that bit. Read the same report on one col_h10_r2 kit (-128.1 at 0930) before writing its row.

### Lever 6. QC structural rows

- cbx_q10 x4 (R): QC-PLAN-R3 cancelled the four kits at 13:09 after a strict-bind failure. The strap-pin move (sidx pins to their stations, 1,450 um -> local) must be in the next plan change, or the relaunch repeats -1 ns.
- sle_stm_v3 (R): so_e pin band to the stream core. Unowned in the posts since 12:40.
- sle_hc1 (R): 8 `wep` copies are in RTL and wait for the next source pin. This is also the endpoint class of lever 2.
- st_a (V, intel2 `fable-fix-qc-sta/kit/{k3,k4}`): `OT_TAIL_SITE copies 156 of 156 sited ... max_hop 524.4 um ... over_380 66` (k4: 148 of 148, 507.1 um, 66 over). 66 hops over the 380 um rule will show at CTS. If they are negative, add one K stage on those groups (FABLE-FIX-QC-STA). N4 st_a kits generated between 10:03 and the tools refresh with de34662bfb5 stop at 3_5.

### Lever 7. Serdes

R: matched-leg star trunk gives rck p1..p99 40 ps before balance (single tree 172) and span 65.2 with 689 pads. The boot-release stop was a private chain placed 544 um off its line; path-local seating moves it from -134.8 to +398.2. V: H20 post-CTS TT -147.83 (the boot endpoint, expected); H21 (both fixes) has no CTS line yet. Not shown yet: routed pair skew and hold cell count. No action beyond lever 1.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| hc0 routed | epyc9 `ot-jobs/sle_hc0__cl929603c0__cl38badc56-route-*/work/{run_route.log,signoff/tt/sta.log,signoff/ff/sta.log}` | DRT 0; TT -29.85; FF internal -21.57 / 152 ends; GRT hold +6.56, GRT TT +12.81 |
| S81 routed hold | epyc9 `fable-fix-s81-col/p774/s2/so_out/ff/sta.log`; epyc2 `autopilot/closed/s81/slice_station__t28__3c913dbdfb/kit/signoff` | non-port n 0 on both; port-start 340 / 191 ends |
| col_h9_r1 rebuild | epyc8 `ot-jobs/col_h9_r1__t1__cl49d7a23e__pv15cef3f7-route-*/work/istations.tcl` | 354 sites at y 1226.88 |
| col_h9_r1 AC test | epyc7 `lanes/s81-col-flow-1118-grtac/.../run_route.log` | GRT-0115, +79,494 cells, hold flat at -64.39 |
| col_h10_r1 | epyc9 `ot-jobs/col_h10_r1__t1__cl95b37463__pv86f5e3b9-route-*/work/run/reports/.../4_cts_final.rpt` | -138.57, one-bit path to `u_d1_11_Y` |
| KV k3 | epyc9 `fable-fix-kv-hg3/k3/gen/kv3_hgi_v1__cl141fc26e/{run_route.log,run/reports/.../congestion-5.rpt}` | hold ends all port_in; west band overflow 44,172 |
| D8e r6 | epyc8 `s81-die-r3-e8/d8e/r6` | elaboration running, bind.log empty at 13:14 |
| mesh_pa | epyc9 `fable-fix-head-mesh/mesh_pa/hd_mesh/run_route.log` | GRT gate TT -32.92, FF hold_est -3.21 (all paths), no DRT line yet |
| st_a k3 / k4 | intel2 `fable-fix-qc-sta/kit/{k3,k4}/gen/*/run_route.log` | tail copies all sited, 66 hops over 380 um |

## 3. The 0930 levers: status

| 0930 # | status | note |
|---|---|---|
| 1 col_h9_r1 | **NOT DONE** | Rows written and in the r6 plan (R). Unchanged kits still launch and fail (V). AC test not at DRT (V). |
| 2 tt_setup_repair | **DONE on main**, patch pass open on epyc7 | 922c27887ac; epyc8 patched (R). |
| 3 D8e + XR | **NOT DONE** | r5 red on 77 `LF_CS_DEPTH`; r6 in elaboration (V). About 50 leaf kits are again in CTS on the d8t form (V). |
| 4 col r0 | **IN PROGRESS** | p6 shorts named: 21 of 25 on the cf macro OBS, fix = halo (R). Bank proof kit in GRT (R). |
| 5 col_h9_r2 | **DONE** | Pilot signed, TT -38.29, internal hold clean (V). The nominal-cap question is closed: wave kits carry NOMCAP r708 in `config.mk` (V). |
| 6 KV | **HALF** | Setup closed on the proof kit (R). Keys not applied yet; west-band congestion open (V). |
| 7 QC | **HALF** | N4 applied as n4_s1, 57 launches since 13:00 (R). First routed kit fails hold (V). |
| 8 HEAD | **IN PROGRESS** | mesh_pa GRT overflow 0, TT -32.92 (V); in detailed route. |

## 4. Stop list (the 09:30 and 12:40 lists stand, plus these)

1. QC: no 10 ps hold pad, and no stall stop below ws 30 at GRT. Do not judge a QC kit as closed on `hold_ws` +5 to +8.
2. QC: no post-route hold ECO that buffers the `m` D pin of the xl banks, and none with only the FF corner loaded.
3. S81: no D8e apply with halo rows on tools older than de34662bfb5. Do not answer a 3_5 `DPL-0004` on col kits one by one.
4. S81: no col_h9_r1 build on the d8t plan, and no roll-out of the allow-congestion hook to that family.
5. S81: no hold work on S81 kits because of a negative FF number in an export line; read `STD_MIN_NONPORT` first.
6. S81 col_h10_r1: no setup repair passes, tap changes or family rows. It is one bit.
7. KV: no hold padding for the 172 k3 ends (port_in). No more GRT iterations on hg / hgi as the answer to the west band.
8. HEAD: do not stop mesh_w1 on the mesh_pa GRT number. Wait for the routed TT.
9. Serdes: no relaunch of H19 or H20 for the boot endpoint; H21 carries the fix.

## 5. Not checked

- The other 151 hc0 hold ends by class: only the worst path was read. The routed TT -29.85 path was not read.
- The sign-off of the sister hc0 kit, hd_ctl (6_final), mesh_pa in DRT, H21 past place.
- Whether the D8e r6 tree tools already carry the three commits (lever 1 is a check to make, not a found defect).
- k3 GRT at its last iteration; the 3,000 gcells outside the west band; hg (non-i) and pc kits.
- col_h10_r2, slice_station (several kits near TT 0 at GRT), dsdv_slice place stops, hd_lep0N (in CTS).
- The distance in lever 5 is from wire delay, not from coordinates.
- The `OT_MAXWIRE` cell count on a normal col kit.
- The live scan read stage and error lines only; its TT pattern did not match most kits, so no fleet-wide TT table this round.

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 09:30 PST (0930): delta on 07:10

Reviewer: FABLE-CLOSURE-STRATEGY-0930. Read-only: no jobs launched, nothing killed, deleted or patched. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0. r708: nominal clock pin cap at sign-off.
Marking: **V** = I opened the file or log this round (09:10 to 09:25 PST hub time). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed (V, failure_breakdown 09:10): S81 42/394, HEAD 24/26, QC 26/130, KV 6/56. Count 393 (R).
Method (V): one scan of every live `ot-jobs/*-route-*/work` dir on intel1, epyc2, epyc7, epyc8, epyc9, epyc10 (176 live route jobs): last stage log, tap spread, post-CTS TT, hold gate, pre-GRT hold pass, GRT congestion report, DRT violations.

## 0. Headline

1. **col_h9_r1 (60 types) cannot pass global route as built: every kit ends on the same hot spot (V).** 9 kits on epyc7 have a final congestion report with a residual of 179 to 288 after 30 extra iterations, and the 7 whose job log I opened end `GRT-0116`; 26 more in GRT show 344 to 775 at iterations 10 to 20. Every one has its overflow in one box, x 660 to 780, y 1200 to 1227 (the die top is 1226.88). Timing on these kits is clean: TT +0.2 to +0.6 (worst -6.0), pre-GRT hold 0 ends, 142k cells. This family is the nearest block of sign-offs on S81 and it is blocked by one station row.
2. **`tt_setup_repair.tcl` has a Tcl error in every runtime tree since 04:19, so new kits lose TT setup repair at CTS and at GRT (V).** Line 134 carries a trailing `# comment` after the closing brace of an `if`. When `OT_TT_SETUP_GUIDE` is unset the `if` raises `wrong # args: extra words after "else" clause`, the step returns rc 1 and the flow keeps the unrepaired DB. 121 live kit copies carry the line (S81 79, QC 26, HEAD 13, KV 3); 27 kits have already logged the fallback.
3. **30 leaf kits are in route on the d8t form with no XR stage and TT -79 to -919 (V).** They cannot sign. Each spends 10k to 71k hold cells and up to 2.7 h in the pre-GRT hold pass.
4. **KV has timing numbers now, and they are all structural (V).** 21 KV kits are in GRT at TT -268 to -1,486. Only io_cor (+156) and hroot (-3) can sign from this wave.
5. **QC: the vclk fix works.** sle_hc0 x2 are the first N3 kits through GRT, now in detailed route (V).

## 1. Levers ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col_h9_r1: `frame_int_o0` station line off the north die edge; meanwhile re-route with allow-congestion | col_h9_r1 60 | S81-COL-FLOW-1118 (re-route), S81-GEOM-OPUS (row), S81-DIE-R3 (delta) |
| 2 | all | Fix `tt_setup_repair.tcl` line 134 and patch the live kit copies | 121 live kits; every kit generated from now (N4, D8e, D23) | WAVE-FLOW-R2 (main + test), S81-COL-FLOW-1118 (kit copies, as for the reset fix) |
| 3 | S81 | D8e apply, then XR mid-wire proof on t3 / t16, then the 58-type key | leaf 74 + kv_leaf 5 | S81-DIE-R3, S81-GEOM-OPUS |
| 4 | S81 | col r0: bank-leaf + relay_sites rows; DRC names on col_h9_r0_p6 | col_h9_r0 60 + col_h10_r0 12 | S81-GEOM-OPUS, S81-COL-FLOW-1118 |
| 5 | S81 | col_h9_r2 to sign-off (pilot ECO + first in-flow route); class table for col_h10_r1 / r2 | col_h9_r2 60; col_h10_r1 / r2 24 | S81-COL-FLOW-1118 |
| 6 | KV | Relay chain keys on hg / hgi after the p2 CTS number; D23g apply; D24 rows for kp and reset | hg / hgi 17, pc 6, pv 16 | FABLE-FIX-KV-HG, KV-HG-OPUS, KV-D23-COMPOSE |
| 7 | QC | N4 apply (st_a stations); class tables for stm_v3 and st_b_v2; first routed sc / hc0 read | st_a 11; sc / hc / fw / fe about 30; 21 provisional | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | HEAD | hd_mesh: TT setup repair on mesh_pa; SDC sha on mesh_w1; patched script on lep_p3 | hd_mesh, hd_lep0N | FABLE-FIX-HEAD-MESH, HEAD-TYPES-OPUS |

### Lever 1. col_h9_r1: one bus, three stations on the die edge

**Evidence (V).**
- epyc7 `.../3fa87b84b18/items/col_h9_r1__t1__cl49d7a23e__pv87d52780/attempt_2/gen/<type>`: `5_1_grt.log` total congestion 11,632 (M6 5,822, M8 5,227, both horizontal) at 12.9 % usage, 30 of 30 extra iterations, `GRT-0116`. `congestion.rpt`: 239 gcells, overflow 288, all in x 660 to 780, y 1200 to 1240.
- Nets in those gcells: `frame_int_o0_is0_q` 1,165 hits, `frame_int_o0_is1_q` 1,041, `u_ist_frame_int_o0_1` 987, `_2` 822, `_0` 533, `u_u_lpl_11_w.q` 420, clk_t22 leaves about 60.
- `istations.tcl` sites the three stations of `frame_int_o0` (1,168 bits) on one line at y 1227, which is the die edge: station 0 x 979 to 1159, station 1 x 667 to 847, station 2 x 355 to 535. The pins are on the north face at x 6 to 260 (M5 / M7). `OT_ISTATIONS placed 11029 flops FIRM`.
- Same box on all kits I binned: cl49d7a23e 179 / 288 final (9 kits, epyc7), 379 to 775 in flight (20 kits, epyc9 / epyc10); clf32cde8d 344 to 397 (6 kits, epyc10).
- Cost of one attempt: place about 20 min, pre-GRT hold pass 0.9 to 1.1 h (6,239 to 7,395 cells), GRT about 1.3 h.

**Root cause (I).** The bus runs 900 um west along the top row band with all three station blocks pinned to the edge. Each block is 1,168 flops in 180 um, so it stacks about 7 rows deep. At station 1 the incoming bundle from station 0 and the outgoing bundle to station 2 overlap above the block, with only the half-plane south of the edge to use. Horizontal demand is twice the bus where the supply is one edge strip. Not checked: whether a macro or halo south of x 660 to 780 narrows the strip further at station 1.

**Fix.**
1. Now (S81-COL-FLOW-1118): re-run route from the existing `4_cts.odb` of the col_h9_r1 kits with the allow-congestion hook. The hook exists (`OT_GRT_ALLOW_CONGESTION=1` read by `gen_phys.py` line 6385 at gen time; it writes `grt_allow_cong.tcl`, which QC kits already carry). P: for the kits on disk, copy that file and its hook block into the kit instead of a regen. Take one kit first and read DRT at iteration 3: 179 gcells of overflow 1 at 0.57 um is within what detailed route usually absorbs, but the block sits on PG pair rows (P).
2. Structural, 0 cycles (S81-GEOM-OPUS, row via S81-DIE-R3 in the delta after D8e): site the `frame_int_o0` stations at y = 1227 - 45 um or deeper, and step stations 0 / 1 / 2 by 10 um in y so in and out bundles do not share tracks. Widen each block from 180 to about 254 um so the bit pitch equals the pin pitch. Class rule for `kit_istations.py`: a station line parallel to a face sits at least one bus width (bits x track pitch / 4 H layers, about 30 um here) inside it.
3. Check the same rule on `frame_int_o1` (stations at y 0 for stages 2 and 3, x 528 to 1038): 28 site groups, so a narrower bus; col_h9_r2 shows residual 15 to 16 at (700, 0) (V).

### Lever 2. TT setup repair is lost in every new kit

**Evidence (V).**
- `rt/current/tools/die_plan/tt_setup_repair.tcl` (rt c860f199a9c6), line 134: `if {$ot_tt_rc eq "grt" && [info exists ::env(OT_TT_SETUP_GUIDE)] && ...} { write_guides ... }     # after any re-route, ...`. All 28 rt trees from 528751c159c8 (04:19) on carry it; 5144e086700c (11-17 23:45) and older do not.
- epyc8 `slice_station__t18` `tt_setup_repair.log`: `Error: tt_setup_repair.tcl, 135 wrong # args: extra words after "else" clause in "if" command`; run_route.log: `OT_TT_SETUP_REPAIR FALLBACK step rc 1: 4_cts.odb unchanged`.
- GRT stage too: hd_spn_wshim_tx `FALLBACK grt step rc 1 ... 5_1_grt.odb is the UNREPAIRED DB`.
- Kits that logged the fallback: slice_station 14, leaf 3, HEAD 10 (hd_ctl, hd_host_n, hd_host_w, hd_mesh x2, hd_spn, hd_st_str x2, hd_turn_a, hd_spn_wshim_tx). The wave hd_mesh kit sits at TT -92.64 unrepaired.
- What the step is worth where the old script ran: col_h9_r1 -9.00 -> +0.64; mesh_w2 -54.94 -> -1.45; leaf t61 -191 -> -80; leaf t2 -379 -> -274.
- Spread: 121 live work dirs hold the bad copy (epyc2 73, epyc9 16, epyc10 12, epyc8 11, intel1 5, epyc7 4). The 08:09 job-start flow refresh replaces old kit copies by rt/current, so it carries the error into older kits at their next stage job.

**Root cause.** A comment after a closing brace on the same line is an argument in Tcl. The `if` only raises when its condition is false, which is every run without a guide file, so both rc bases fail.

**Fix.**
1. WAVE-FLOW-R2: move the comment to its own line on main. Add a test that sources the script body with `OT_TT_SETUP_GUIDE` unset for both `placement` and `grt` (a Tcl parse of the `if` word count is enough).
2. S81-COL-FLOW-1118 pattern: copy + mv of the fixed file into every live work dir and every per-item gen dir (`items/<item>/gen/<item>/`), all 7 hosts. Not `sed -i`.
3. Kits that already passed CTS with the fallback keep an unrepaired DB. For types within 60 ps of the gate, re-run the step on `4_cts.odb` before judging them (slice_station t48 -163 and hd_mesh are outside that; read after repair).

### Lever 3. Leaf: D8e, then XR mid-wire

**Evidence (V).**
- 21 leaf kits in GRT: TT -79.5 (t61), -97 (t62), -192 (t57), -250 (t28, t40), -274 (t2), -298 to -395 (t59, t70, t22, t5, t47, t46), -457 to -529 (t21, t42, t54), -639 to -919 (t60, t67, t23, t52, t72, t54__cl501e5681).
- t52: `OT_VPW_BANK placed 317 FFs` = no XR in the netlist (0855 rule: 317 no XR, about 1,219 XR at the bank).
- Hold on the same kits: gate WNS -150 to -253 on 4k to 20k ends; pre-GRT pass adds 9.7k to 71k cells (t22 71,211, t28 68,813, t72 64,149 on 386,687) in 0.1 to 2.7 h; t22 / t28 / t61 / t70 still end with open ends.
- Tap spread 129 to 389 ps (t52: 287 to 601, core clock `clk_c1` 601 against target 450).
- R: D8e r4 crashed on the t40 taps; r5 on plan a30d6c6f (t40 back on rd2) was moving to epyc2. I found no r5 bind log on epyc2 or epyc8 at 09:20 (V). XR-MID-1 is on main (c4f44b2c1d2), rows for 58 types, unbuilt.

**Root cause.** As 0855 fix 2: the VS-to-bank wire is in one cycle. Second class (I): the hold cell count follows the tap spread, and the spread follows core clock pins whose pin + internal insertion is above the tap target.

**Fix.**
1. S81-DIE-R3: r5 bind, apply D8e. Run `reset_anchor.resolve_plan` and `taps.grid_explicit_sites` first (13 s, already done on a30d6c6f, R).
2. S81-GEOM-OPUS: t3 and t16 proof kits on the D8e tree with `budgets.vpw_xr_mid_types` + `OT_S81_VPW_BANK=1`. Read `OT_VPW_BANK placed N`, post-CTS TT and the tap spread. Then the 58-type row file as one delta.
3. P, after the first XR kit: if the spread stays above 150 ps, set the tap target per type to the slowest core clock pin (pin + internal) instead of 450, so the taps are delayed up to it; the hold cells then fall with the spread.

### Lever 4. col r0 (72 types)

**Evidence.**
- V: 38 of 72 rows are place FAIL in the stage table: 47 S81 rows on `RESET v5 refuses empty explicit buffer set`, 8 on `OT_HOOK_COVERAGE relay_mid`. R (S81-COL-FLOW-1118 08:22 to 09:05): both fixed on main (235d4be8301, 096be78133f) and in the kit copies, including the per-item gen dirs; retry keys in.
- V: the only r0 kits past CTS: p1 TT -46.8 (10,530 hold cells, 7,290 s), p5 -11.9, p6 -1.2 at CTS but **-88.89 after GRT** (the GRT setup repair made it -133.97 and was restored). p6 is in detailed route at iteration 25+, flat at 32 to 39 violations since iteration 17 (29 M5 shorts, 2 M4 spacing).
- R (S81-GEOM-OPUS): r0 has macro-to-macro paths up to 1,740 um with 0 stages; RELAYSITE-1 row proven at placement (127 / 128 FIRM).

**Fix.** S81-GEOM-OPUS: bank-leaf rows + relay_sites on both cl0045af7b and cl9f71e63d into the delta after D8e; route the bank proof kit to sign-off. S81-COL-FLOW-1118: on p6 name the 29 M5 shorts (nets and whether they sit on PG M5 stripes) before any ECO; the TT -88.89 means this kit is a DRC probe only.

### Lever 5. col_h9_r2 and col_h10

**Evidence (V).**
- col_h9_r2 pvea45273b: TT +0.1, pre-GRT hold 0 ends (3,738 cells), GRT residual 1, `hold_ws 25.19 margin 25 OK`. Cleanest S81 kit in flight.
- Pilot pv11b6518d ECO started 09:07 on epyc7 (`s81-col-flow-1118-pilot/eco_1118`); R: DRC 2, TT -46.9, FF hold -62 on 345 ends under r708.
- col_h10_r1 (7 kits): TT -87.6 to -146.0 at CTS, setup repair gains 0; GRT iteration 5 overflow 56k around x 800 to 1100, y 200 to 300. col_h10_r2: TT -128.1.
- `failure_breakdown` TOOLS-LAG still lists the s81 tree as missing fixes; in-flow hold repair runs on range clock pin caps (I).

**Root cause (I).** The 345 hold ends at -62 on a kit that had 5 ends at -5 in flow are the range-cap / nominal-cap difference, not a design change.

**Fix.** S81-COL-FLOW-1118: let pvea45273b route and re-sign under r708; if hold fails the same way, the class fix is nominal clock pin caps in the in-flow hold passes (r708 into the kit libs), not an ECO per type. col_h10_r1 / r2: one class table of the TT ends at `4_cts.odb` (start, end, wire um) before any row.

### Lever 6. KV

**Evidence (V).** TT after the pre-GRT pass: hg -502 (kv3_hg), -805 to -864 (hg_v1, v1p2 to v1p5); hgi -268 to -340 (v1 x2, v2, v3), -705 (v4), -792 (v7); pc -468, -815, -1,069, -1,360, -1,486 (pc_v3); hroot -3.2; io_cor +156.2. GRT overflow in flight: hg 42k to 52k, hgi_v1 40k to 44k around x 0 to 200, y 1000 to 1100, pc_v1 17k to 20k. Hold pass: pc_v3 18,678 cells in 15,353 s. Proof kit p2 (relay chain keys): last log `2_1_floorplan` at 09:20, no CTS number yet. R: D23 / D23b failed on one hub_Wo EMIT; D23e / f / g gates due about 10:40.

**Root cause (R, FABLE-FIX-KV-HG).** Unregistered 1.0 to 3.2 mm wires in every failing class; the hst / ftg relay flops were not placed (0 of 9,450).

**Fix.** FABLE-FIX-KV-HG: p2 CTS ends table. KV-HG-OPUS: if hst and lpad classes clear, item_env keys on the 17 hg / hgi types and relaunch. KV-D23-COMPOSE: apply g > f > e. D24 rows for what p2 leaves (kp core to core -239, reset to core -309) and for pc. Route io_cor and hroot to sign-off now; hroot needs TT setup repair to work (lever 2: 3 KV kits carry the bad script).

### Lever 7. QC

**Evidence (V).**
- sle_hc0 x2 passed GRT (`hold_ws 6.56 / 6.63`, TT +18.4 / +11.9 before GRT, 408,738 / 394,442 cells), in detailed route.
- In GRT: sle_sc_v1 TT +9.2; slw_sc_v1 x3 -17.4 to +11.6; slw_fw_v1 x2 +2.2 / +54.1; slw_fe_v1 +55.4 (28,001 hold cells).
- Outside the gate before route: sle_st_a_v1 -654, slw_st_a_v2 -462, slw_st_a_v1 x2 -235 / -242, sle_stm_v3 -203, sle_st_b_v2 -67.7.
- The pre-GRT pass in these kits still pads port_in (517 to 2,742 ends left at -49 to -165); ee7566bd8b7 reaches only kits generated after 08:04.
- 26 QC kit copies carry the bad setup-repair script.

**Fix.** QC-PLAN-R3: N4 apply (st_a stations). QC-N-OPUS: k2 routed. QC-TYPES-R3: read routed TT and internal hold on sle_hc0 first; class tables for stm_v3 and st_b_v2 (no row exists for either). N4 kits must be generated after the lever 2 fix.

### Lever 8. HEAD

**Evidence (V).**
- mesh_w1: `5_1_grt.log` ended 09:12 with `HOLD-SDC-MISMATCH stage repair_timing: golden SDC /work/constraint.sdc sha 9de86b68 != kit OT_SIGNOFF_SDC_SHA ae5020a4`, after the 35,109-cell hold pass. A GRT-only relaunch started 09:16.
- mesh_pa: CTS done, taps 401 to 462, hold gate -131.42 on 9,462 ends. The kit has no `tt_setup_repair.tcl`, so TT -28.36 (R) is unrepaired; the same step took mesh_w2 from -54.94 to -1.45.
- lep_p3: in CTS; its kit copy has the bad script.

**Fix.** FABLE-FIX-HEAD-MESH: run the fixed setup-repair step on the mesh_pa `4_cts.odb` before the hold pass result is used (hold padding on an unrepaired DB fixes the wrong slack). HEAD-TYPES-OPUS: if the 09:16 GRT run stops on the same sha, set `OT_SIGNOFF_SDC_SHA` to the kit SDC that the hold pass used; patch lep_p3 by copy + mv before its CTS ends.

## 2. Stop list (the 07:10 and 08:55 lists stand, plus these)

1. No unchanged relaunch of col_h9_r1 from kit_rtl. It ends at the same box after about 2.7 h. No more GRT iterations either: 30 were flat.
2. No triage of a near-gate TT number from a kit whose log says `OT_TT_SETUP_REPAIR FALLBACK`. Repair first.
3. No reading, ECO or hold work on the 30 leaf route kits of the d8t form (`OT_VPW_BANK placed 317`).
4. No ECO on col_h9_r0_p6: TT -88.89 after GRT. Use it for the M5 short names only.
5. KV: no hold padding or ECO on a kit with TT under -250; no hg / hgi keys on wave rows before the p2 CTS number.
6. hd_mesh: no sign-off attempt on mesh_pa without setup repair; no second padding round (07:10 item stands).
7. QC: no port_in hold cells; no N4 kit gen before the setup-repair fix is in rt/current.
8. Do not raise the per-type hold margin to clear the col pilot's 345 ends before the nominal-cap question is answered.

## 3. The 0710 levers: status

| 0710 # | status | note |
|---|---|---|
| 1 D8e bind | **NOT DONE** | r3 error fixed by tools (R). r4 crashed 08:37 on 8 t40 added taps (R, 0855). r5 on a30d6c6f not finished; no bind log found at 09:20 (V). t40 taps re-sited, gate queued (R). XR-MID-1 on main, unbuilt. |
| 2 RESET v5 empty set | **DONE** | main 235d4be8301 + kit copies and per-item gen dirs patched by 09:05 (R). 47 rows still show the old FAIL until the retry tick (V). |
| 3 col_h9_r2 ECO, bank proof | **IN PROGRESS** | ECO dir created 09:07 (V). Bank proof kit: relay_sites proven at placement, route restarted after the reset fix (R). |
| 4 QC N4 / measured hold | **HALF** | vclk fix proven: sle_hc0 x2 through GRT (V). N4 publish / apply still running (R). n41d bind 0 errors, k2 kit running (R). |
| 5 hd_mesh | **MECHANISM FOUND** | R: -141.74 = declared tap window 76 + uncertainty 25 + guard 45 on zero-logic cross-tap pairs. mesh_pa cuts internal ends 11,163 -> 5,251 (R). mesh_w1 lost its GRT to an SDC sha check (V). |
| 6 KV first evidence | **DONE, premise corrected** | KV kits do reach CTS in the sealed ot-jobs dirs; 21 TT numbers above (V). D23 / D23b failed; e / f / g binding (R). hub_C node move not checked. |
| 7 serdes H18 | **SUPERSEDED** | 0855: H18 is recipe evidence. H19 (16 rck roots, north taps on the strip) is at floorplan (V). H18 in GRT: TT -159.87 after CTS, 415k non-tap cells (V). |
| 8 mergex | **DONE** | mm6 signed under r708: TT +161.22, FF +16.18 (R). mm15r stopped. |
| r708 in the die trees | **OPEN** | TOOLS-LAG 09:10 still lists r708 missing on qwen_kvsys and s81_head, and 93 fixes missing on s81 (V). |

## 4. Not checked

- Whether detailed route absorbs the col_h9_r1 residual with allow-congestion; what lies south of x 660 to 780 at the north edge.
- D8e r5 bind result; any XR kit.
- The path classes of col_h10_r1 / r2, QC stm_v3 / st_b_v2, slice_station t18 / t46 / t6 (-917 / -577 / -419, all with the setup-repair fallback).
- Routed numbers of any QC N3 kit, of mesh_pa, lep_p3, H19 and the col pilot ECO.
- KV p2 beyond floorplan; PV CLAND on v2 / v6; D23e / f / g.
- Why the pre-GRT hold pass takes 0.9 to 4.3 h (single thread, R) on col, leaf and kv3_pc.
- Die STA on the real clock (S81, HEAD): unchanged.

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 07:10 PST (0710): delta on 05:10

Reviewer: CLOSURE-STRATEGY-0710 (Opus; Fable is at its weekly limit). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. r708: clock pin cap is nominal at sign-off.
Marking: **V** = I opened the file or log this round (07:10 to 07:40 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed (V, failure_breakdown 07:10): S81 42/394, HEAD 24/26, QC 25/130, KV 6/56. S81 kit rows: 316 running, **27 other flow error** (back up from 0 at 06:25), 5 cancelled, 3 kit input missing.

## 0. Headline

1. **D8e has not been bound. Its 05:41 rebind ended at about 06:13 with 80 errors, and nobody has posted about it (V).** epyc8 `s81-die-r3-e8/d8e/r3/bind.log` reports `errors 80`. One is an EMIT error: `relay_depth col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97: 3 row(s) matched no internal sink ['u_r0_u_y_cc_1_0.o','u_r0_u_y_cc_3_0.o','u_r0_u_y_x2_3_0.o']`. The other 79 are leaf / kv_leaf `LF_CS_DEPTH ... no bound module file`. `leaf_cs_depth.py` reads `s81p_<type>.sv`, and the failed emit never wrote those files, so the 79 are a cascade. G0 RC 1 with 2 errors (the D8d control errors). The bind ran on tools `74354c18`, which do not contain b8f543dd448: S81-GEOM-OPUS pushed that fix (relay_depth compared by sv_id, `u_r0.u_x == u_r0_u_x`) at 05:5x for exactly this error. Nothing has been written in r3 since 06:32, no bind is running on epyc8, and S81-DIE-R3 has not posted since 05:41. The 07:40 apply ETA will not hold. Everything on S81 that depends on the plan is waiting on this bind: XR, reset relays, leaf stride, the serdes rck pin, the face-clear rows and the 15 setup stops.
2. **27 S81 col kits fail at `3_4_place_resized` on one reset-tool assert (V).** `reset_chain_spread.tcl` line 87 in the d8t tree, `tools/die_plan` (header `PRIVATE CANDIDATE v5`; the file is not on main): `RESET v5 refuses empty explicit buffer set`. Split: col_h9_r2 clce45cab5 11, col_h9_r1 cl49d7a23e 10, col_h9_r2 clb8d86cd5 3, col_h9_r2 clc9ad8f7e 2, col_h10_r1 cl95b37463 1. Each one fails 15 min into resize.
3. **The routed col pilot is still on disk, and nobody has taken it (V).** On epyc10, both `/srv/opentallas-scratch{,2}/.../3fa87b84b18/items/col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2` hold `6_final.odb` (01:03 PST) and `signoff/signoff.json` (TT -46.87, DRC 2, hold 5 ends at -5.07, per 0510). Because of the DRC 2 the r708 sweep skipped it. The wave has relaunched the type from scratch (attempt 5, in gen on d8t).
4. **hd_mesh: tap balance worked (399 to 462, spread 63 ps, was 128), but hold demand barely moved (V).** mesh_w2 `pregrt_ff_hold.log`: RSZ sees 22,446 hold endpoints, WNS -141.74, TNS -447,851. OT_HOLD_GATE: 15,380 ends, 1,036 forwarded ring inputs on 2 clocks, contract in_min -90, structural limit -183. Repair has run since 06:05. The 0510 premise ("the 128 ps tap spread is the hold demand") was only partly right.
5. **Serdes H18 rck tree closes at placement (V).** epyc9 H18 `4_1_cts.log`: `OT_STB_SPAN io_pma_rck[0] sinks 26277 min 1948.4 max 2058.0 span 109.5 limit 110.0 PASS`, using 1,012 delay inverter pairs. It is now in GRT (`5_1_grt.tmp.log` 07:19).
6. **KV still has no CTS number (V).** I found no `4_1_cts.log` under `runs/qwen_kvsys` on epyc7 / epyc9 in the last 15 h. The last HG6 PV kits stopped at `3_5_place_dp` (02:4x to 03:1x) and were then superseded. The 10 retry rows launched at 07:06 on D22 are at kit_rtl (V, wave state).
7. **QC: the measured-hold fix is in code but not yet proven on a kit (R + V).** QC-FLOW-1118 e1ce3e0b234 (05:53): per-clock means, IO vclk bound to the pooled mean, `::nka_blk` made global. Wave state: sle_sc_v3 a3 at place, cbx_q10 a4 at place, sle_sc_v1 a2 enqueued. No stage pass yet.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Rebind D8e (plan d396b7d6) on tools >= b8f543dd448, then LATCHECK / G0 / apply | leaf 75 + kv_leaf 5, serdes 11 rows, face-clear rows, 15 setup stops | S81-DIE-R3 (no post since 05:41) |
| 2 | S81 | `reset_chain_spread.tcl` v5: an empty BUF set is a no-op, not an error | 27 col kits (5 type groups) | S81-COL-FLOW-1118, S81-TYPES-R3 |
| 3 | S81 | ECO the routed col_h9_r2 pv11b6518d (2 DRC + 5 hold ends + TT 4.87 ps), r708 re-sign; route the bank-leaf proof kit | col 215 (family proof) | S81-TYPES-R3 + CAPSKEW-ECO; S81-GEOM-OPUS |
| 4 | QC | N4 apply (N4D derived-R8 pass 2) -> N4.1 kit k2 to routed sign-off; read the 6 measured-hold relaunches at GRT | st_a 11; sc/su/fe/fw up to 29; cbx | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 5 | HEAD | hd_mesh: read mesh_w2 after repair (TT, cell count); if TT < -42, take a launch/capture class table of the hold ends before any padding | hd_mesh | HEAD-TYPES-OPUS |
| 6 | KV | First hg/hgi CTS read on D22; D23 -> D23b apply; CLAND facegrow read on pv_v2/v4/v6 at 3_3 | pv 16, pc 6; first evidence for hg/hgi 19 | KV-HG-OPUS, KV-D23-COMPOSE, KV-D22-ROWS |
| 7 | S81 | Serdes H18 to routed + r708; pad-clock trunk rows in the D8e rebind | serdes 11 | S81-CORES-OPUS, S81-DIE-R3 |
| 8 | S81 | mergex_mm3b: r583 internal hold ECO on the routed DB (FF -3.45, 62 ends) | svc 16 (last core) | S81-CORES-OPUS |

### Lever 1. S81 D8e bind

**Evidence (V).** As in headline 1. `r3/pre.out` reads PLAN-GATE-PRE PASS, findings 0 (06:32), with 50 inherited station/relay sites over hard cores. `bind.log` is 42 lines long: 1 EMIT error, 29 LF_CS_DEPTH lines shown (80 in the count), 10 RESET_ANCHOR info lines. `TOOLS_SHA` = 74354c18d2f9.

**Root cause.** bind.py on 74354c18 matches `relay_depth` rows by dotted instance name. Bound r0 col instances are flattened (`u_r0_u_y_cc_1_0`), so the 3 u_r0 rows match no sink. Emit stops, no bound module is written, and leaf_cs_depth then fails every XR leaf type. P: there is one real error, not 80.

**Fix.**
1. S81-DIE-R3: re-run the D8e bind on the same plan d396b7d6 with tools at or after b8f543dd448 (on main). The alternative is to drop the u_r0 `*.o` rows. Do not strip the XR rows.
2. After the bind, check that LF_CS_DEPTH reads 0 on all 80 leaf / kv_leaf types. If it does not, it is a second class (plan stage vs bound RTL stage depth), and leaf_cs_depth names the class per type.
3. In the same rebind: the pad-clock trunk rows for the moved `io_pma_rck` pin (lever 7), plus S81-GEOM-OPUS `rows_face_clear_d8e.json` (de8ad49d0f1b: t40 fc6, t29 fc5, 0 cycles). Both are row-only and were proven on D8e (R). If adding them would restart the bind proof, they go in as the first delta after apply instead.

### Lever 2. Col reset-chain spread v5 assert

**Evidence (V).** epyc2 kit `col_h10_r1__t1__cl95b37463__pve28d14fa/attempt_5`, `3_4_place_resized.log`: PLACE-HPWL 1.002, NOCONVERGE OK, then the assert. `config.mk` sets `OT_RESET_CHAIN_SPREAD = 1` (reset_replicate copy-depth chains). The script walks from each chain root through BUF/INV cells and collects only the BUF cells that GPL inserted. It errors when it finds none (line 87). Also in the same log: OT_PLACE_WIRE_RATIO 14 violations, worst 28.07, all on the `u_bound.u_d11_11_Y_r*_s0` reset copy stages (21 um direct, 589 um built). This is the chain that the spread step exists to fix.

**Root cause.** The v5 candidate assumes that GPL buffered every reset root. On these col types the copy-depth roots have low fanout, so GPL inserted no BUF, and the "nothing to prune" case becomes a hard error.

**Fix.** An empty `rc_bufs` logs `RESET v5 no GPL buffers: nothing to prune` and goes on to the spread. Keep the CLOCK-net error and the INV preservation. Put the fix in the tree tools / rt, and land the candidate on main with a test for the empty case (test_reset_chain_spread.py exists in the tree). Then relaunch the 27 rows. P: after the spread, the u_d11 wire-ratio paths are what the TT gate should be read on.

### Lever 3. Col family proof by ECO

**Evidence (V).** As in headline 3. The kit DB includes `5_1_grt.odb`, `6_final.{odb,def,spef,v}`, the LEF and the typ lib. R (S81-GEOM-OPUS 07:10): bank-leaf gate_bl1 / bl2 PASS (bind 0, LATCHECK 873/873, G0 0 new). The proof kit col_h9_r0_p2 cl0045af7b (r0 worst 1,740 um family + ROM move) is at kit gen on epyc8. The rt4 probe on the attempt_5 floorplan is reading the u_y_rt_4a_0 / 4b_0 sources so that FIRM relay_sites can be placed (0 cycles).

**Fix.**
1. S81-TYPES-R3 (+ CAPSKEW-ECO form): on the existing attempt_2 routed DB, name and fix the 2 DRCs (detail-route ECO). Then run the capture-skew / hold-pad ECO on the 5 hold ends and the worst TT ends (core to core `u_u_e*_u_w -> u_u_bn*`), and re-sign under r708. That is about 5 ps of TT and 5 ends of hold. No rebuild is needed.
2. S81-GEOM-OPUS: take the bank-leaf proof kit to routed sign-off; put the rt4 FIRM relay_sites rows on both cl0045af7b and cl9f71e63d.
3. P: a signed r2 plus a signed r0_p2 proves both col sub-families on d8t rows. The other 50+ placed col kits then need the same ECO, not new rows.

### Lever 4. QC N4 / N4.1 and the measured-hold relaunches

**Evidence (R).** N4: the N4C LANE_ASBUILT error (delivered 10 vs 7) was fixed by setting `lanes[].fixed_cycles 3` on sl_W0/W2/W4_fw__x_fw_st_a. The N4D pass-1 bind is clean apart from the expected 30 R8_STALE. Derived-R8 pass 2 has run since 06:48; publish + apply around 07:45 (QC-PLAN-R3 06:56). N4.1: n41b has 15 errors: R8_STRAP_PAD 12 on sle_ctl__cl503337ff (26 > 25) and __cl67434795 (16 > 15), TYPE_SPLIT 2 and EMIT 1. The x_fe_o +1 station moves R8 by one cycle at ctl. n41d (r8_strap_pad_max 26 / 16) is running (QC-N-OPUS 06:3x). V: the measured-hold relaunches are in place / gen; sle_ctl__cla4f6f12f FAILs kit_rtl with `captured reset identity` on N3.

**Fix.**
1. QC-PLAN-R3: apply N4 as composed.
2. QC-N-OPUS: rebase n41d onto the N4 tree. Raising the ctl strap pad limit is a real +1 R8 on two ctl types: check the receiver latency in LATCHECK rather than only raising the limit. Then take kit k2 to routed sign-off under r708.
3. QC-TYPES-R3: read `OT_VCLK_MEASURED_CLOCK` and the hold_ws line in `5_1_grt.log` of sle_sc_v3 / slw_fw_v3 / sle_sc_v1 / sle_su_l1 / slw_fe_v2 when they reach GRT. Three of them were at CTS wns 0.00 / -5.29 / -33.43, so they are the next sign-off candidates on QC.

### Lever 5. hd_mesh hold after tap balance

**Evidence (V).** As in headline 4. CTS took 20 min; the repair log stops at iteration 0. R (HEAD-TYPES-OPUS 06:30): TT at CTS -1.45 (7 cells), cross_tap 10,130 of 15,372 ends.

**Root cause (P).** With 63 ps of tap spread, -141.74 cannot come from tap skew alone. The remaining about 80 ps is either the forwarded ring input class (1,036 inputs on 2 clocks, contract in_min -90) or same-clock short paths in `u_core.u_la.u_ln.u.u_ep.xpn_f` (the worst endpoint). Padding 15 k ends is the cost profile of mesh_w1, which lost TT -49.56 -> -68.34 on 37,912 cells.

**Fix.** HEAD-TYPES-OPUS: let the repair finish and read routed TT and the inserted cell count. If TT >= -42 and hold >= 0, sign and export. If not, before any new form: take the hold ends from `4_cts.odb` (launch tap, capture tap/clock, path depth), bin them, and fix the largest bin at its source. For the ring class that means a capture-side offset on the forwarded ring clock. For xpn_f it means 1 to 2 min-delay cells at the D pin in RTL synth constraints. Do not pad. Keep mesh_w1 alive until mesh_w2 has a routed number.

### Lever 6. KV first timing evidence

**Evidence.** V: no KV CTS log (headline 6). R: D23 strict bind since 06:20 (plan add04d1e8a2d: tail split `kv3_pv.*`, 68 pc taps, efault, hub_Wo 11 cores). D23b = D23 + 59 PV raw-stage band rows, already binding. D23c = D23b + reach rows + lite+narrow rings on all 5 hubs (hub_C 357,873 -> 238,112 cells, proven formally and in lock-step). Its bind waits on the reach code landing on main. hub_Wi host split: gate clean, shell 299,999 cells. hub_C clock-node move BLOCKED: the e9 die clock tree source (`kv-clk-r2/runs/e9`) was deleted, so the reserved-rect collision on pvfin_hi stays at 1.

**Fix.**
1. KV-D22-ROWS: as soon as one of the 10 retry rows (hg_v3, hgi, hgi_v5, hgi_v6) reaches CTS, read the OT_TAP_BALANCE and wns lines. This is the first KV evidence and it decides D24.
2. KV-D23-COMPOSE: apply D23, then D23b, each as soon as it is green. Read OT_CLAND for the two writer-face START windows on pv_v2/v4/v6 (the first run with facegrow 58211f43d07). If they fail, the fix is in the facegrow law (tools), not in plan rows.
3. hub_C node move: rebuild the e9 die clock kit (the inputs are gone) before any node re-site. e9 is an x-mirrored DME template, so check the mirror instances in the same run. Do not hand-edit the rect.

### Lever 7. Serdes H18 and the die trunk

**Evidence.** V: headline 5. R: H18 rail check 6,726 rows, 0 bad. H17 under r708: TT -69.66, FF -17.09, not signed. The die trunk (about 1,115 um, 3 hops <= 405 um, M8/M9) still has no plan field.

**Fix.** S81-CORES-OPUS: route H18, then run in-flow sign-off + the r708 re-sign. If TT is within about 30 ps, use the sd9he ECO form on the routed DB. S81-DIE-R3: put the trunk in as explicit die clock rows in the D8e rebind (lever 1.3). Compare the measured rck insertion at the sinks (1,948 to 2,058 ps from the pin) with the die trunk arrival budget before export.

### Lever 8. mergex

**Evidence (R).** mm3b r708: NOT SIGNED, TT +161.72, FF -3.45, 62 internal violators. mm6 in detailed route (iter0 20 k violations). mm3r at CTS hold margin (HM 30, 36,994 ends). mm15r in GRT.

**Fix.** S81-CORES-OPUS: the r583 internal hold ECO on the mm3b routed DB has 161 ps of TT slack to spend on 62 ends, so it should close. Run it now in parallel with mm3r / mm6, and stop mm15r.

## 2. Stop list (the 05:10 list stands, except where struck below, plus these)

1. Do not treat D8e as "binding / applying ~07:40". The bind failed at about 06:13. No publish from r3, and no partial apply that leaves out the leaf XR rows.
2. Do not read the d8t leaf / kv_leaf / iqf kits relaunched at 06:04 as evidence. They have no XR and will stop again at -260 to -734 ps post-CTS TT. Do not re-triage them.
3. Do not relaunch the 27 RESET v5 col rows before the empty-set fix: each one refails in 15 min.
4. Do not treat a fresh attempt 5 as the only path for col_h9_r2 pv11b6518d. The routed DB exists. Do not delete or clean epyc10 attempt_2.
5. hd_mesh: no second pre-GRT hold padding round, and no new mesh form before mesh_w2 has a routed number.
6. mergex: stop mm15r (the 15 ps form; hslice showed there is no room).
7. KV: no hand edit of the hub_C clock rect; no D24 ring decision before one KV CTS number.
8. QC: no N4.1 rows into N4. Do not raise the ctl R8 strap pad limit without a LATCHECK of the receivers.
9. Serdes: still no `serdes_shore_delta.py` rerun on D8e.

## 3. The 0510 levers: done, stale or wrong

| 0510 # | status | note |
|---|---|---|
| 1 col ROM rows | **DONE** (rows) / **STALE** (ECO) | 1,140 rows stripped 05:41 (R, S81-DIE-R3). 149 one-ROM moves gate PASS, `read_loop_place.py` on main 4ce3ad6120c (R). The col_h9_r2 ECO was not started (V); now lever 3. |
| 2 leaf D8e + interior class | **BLOCKED** / **partly answered** | D8e bind failed (lever 1). Interior windows: t40 and t29 are the face-window class, closed by 0-cycle face-clear rows fc6 / fc5 (R). fc2 / vp1-3 not applied: the t25__cl55642d17 ft0 reg cannot be re-sited, so it is still open. t24 / t68 not imaged. |
| 3 QC measured hold | **DONE in code** | e1ce3e0b234 + the nka_blk global (R). Kit proof pending (lever 4). |
| 4 KV D23 | **IN PROGRESS** / **STALE** | D23 / D23b binding. "Read hg/hgi at CTS now" could not happen: no KV kit has reached CTS (V). |
| 5 QC N4 / N4.1 | **SLIPPED** | Apply 05:30 -> about 07:45 (LANE_ASBUILT fixed_cycles, then R8 pass 2). The N4.1 k1 kit failed kit-rtl on the 34-error bind; n41d is pending. |
| 6 serdes | **ADVANCED** | H18 rck span PASS, in GRT (V). The die trunk field is still open. |
| 7 HEAD | **PREMISE WRONG** (hd_mesh) / **ADVANCED** (lep0N) | Taps were balanced to a 63 ps spread, yet hold is still -141.74 on 15 k ends (V), so tap spread was not the main hold source. hd_lep0N: RTL fix 0dcc215 is building as lep_p3 on epyc9 (moved from epyc10 when the docker create stalled, R). |
| 8 svc mergex | **STALE** | mm3b r708 NOT SIGNED -3.45. mm15r still running against the 0510 stop (R). |
| 0510 headline 4 (QC kits hidden as `_LAYOUT_RENDER`) | **DONE** | The classifier now files it as FLOW (R, QC-FLOW-1118). |

Also: r708 was approved for all four dies at 06:02 (COORD). The 07:10 TOOLS-LAG still lists r708 as missing on the s81, s81_head and qwen_kvsys trees (it is not named for qwen_compute: 141 more not shown). So in-flow hold repair on those kits still runs against range clock-pin caps while sign-off uses nominal ones (V, breakdown). P: expect small hold over-fix and small setup loss until the trees carry ad8672055e3. Re-sign remains the rescue path.

## 4. Not checked

- Whether LF_CS_DEPTH clears once emit succeeds (lever 1, P).
- The routed col_h9_r2 DRC names; the bank-leaf proof kit beyond gen.
- mesh_w2 repair outcome; lep_p3 beyond synth start.
- N4D pass 2, n41d, D23 / D23b bind results.
- Any measured-hold relaunch at GRT; H18 GRT overflow.
- dsdv_slice (20), slice_station t6, bk_sel / eng / gunit / iqf / seqhost: wave rows only.
- Die STA on the real clock (S81, HEAD): unchanged, 0 measured hold pairs (R).

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 05:10 PST (0510): delta on 03:20

Reviewer: FABLE-CLOSURE-STRATEGY-0510 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. r708: clock pin cap nominal at sign-off.
Marking: **V** = I opened the file or log this round (05:10 to 05:50 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

Signed types by family (V, plan cache 05:10): S81 42/394 (slice_station 41/46, col_h9_r2 1/60, everything else 0: leaf 75, col 215, dsdv_slice 20, svc 16, serdes 11, kv_leaf 5, bk_sel, eng, gunit, iqf, seqhost). HEAD 24/26 (open: hd_mesh, hd_lep0N). QC 24/130 (hc 7/18, fe 4/9, su 4/9, stm 2/11, fw 1/11; 0 of st_b 12, st_a 11, sc 9, cbn/cbf/cbx 18, ctl 7). KV 6/56 (0 of pv 16, hgi 11, hg 8, pc 6, hub 5).

## 0. Headline

1. **The D8e plan now in bind carries 1,140 relay rows that break the col config sequencer (V).** epyc8 `s81-colgen-1/ev/d8e_rd.json` (sha1 c24b3f8b72b8, the plan S81-DIE-R3 took at 05:08): 2,058 `relay_depth` rows; 480 `u_c*_*.addr_in` + 480 `ce_in` + 180 `u_s*.q*` = 1,140 rows on 168 col types, identical to `d8d_rd.json`. FABLE-FIX-S81-BANKLEAF measured at 04:56 (R, verilator on `ot_s81_cfg7_seq`): one stage on one ROM of the fixed-latency read loop captures the wrong word; bind and LATCHECK accept it. The S81-DIE-R3 post does not mention the alert (V, 0 matches). These rows span 420 to 640 um, just over the 405 um reach.
2. **Col is 215 of the 352 unsigned S81 types and its one routed member is ECO-sized (V).** epyc10 `col_h9_r2__t1__cl774acf45__pv11b6518d/attempt_2` sign-off: DRC 2, TT -46.87 / 131 ends, internal FF hold 5 ends at -5.07, 102 unconstrained. The worst TT path is core to core (`u_u_e*_u_w` -> `u_u_bn*`), the bank-leaf class. No relay rows are in that kit.
3. **`5_global_route.rpt` is not a TT number (V).** Leaf t11 reads -5.30 there and -288.97 at the TT gate of the same DB; t15 -17.59 / -350.29; kv_leaf t4 -4.71 / -259.65. The GRT repair session is FF-only (`tt_setup_repair.tcl` header); the TT repair on t11 moved -353.00 -> -288.97 with 404 cells. This answers the 03:20 open item: the 14 strip stops are real at TT.
4. **QC kits with clean GRT die on the measured-hold bind when pin registers sit on more than one clock (V).** `vclk_measured_hold.tcl` line 131 errors unless `ncl == 1`. Five kits: N3 sle_sc_v3 (04:4x today, CTS wns -59.25, GRT overflow 0, `clocks 3`), N1B slw_fw_v3 (CTS 0.00, `clocks 4`), sle_sc_v1__cl7479a5ec (-5.29), sle_su_l1__cl5ea486db (-33.43), slw_fe_v2__cle312294d (-88.40). The wave row for sle_sc_v3 reads `_LAYOUT_RENDER ... local_density`, so the class is hidden. No QC lane post names it.
5. **S81 leaf GRT overflow has a second class that row stride 2 does not address (V).** t25__cl431c660f (fixed by the pilot) is the south face. t24: 566 congested gcells in one window x 850-950, y 300-450, M6 6,368 + M8 11,182 of 18,328. t68: 524 gcells at x 500-550, y 200-250, M6 5,616 + M8 6,253. t25__cl55642d17: 5,122 gcells at x 200-300, y 350-450, M6 69,907 + M8 21,090. All interior, all on the horizontal layers M6 and M8 only.
6. **KV has no CTS number on the current plan family (V).** 27 KV-HG6 kits have `3_5_place_dp` as their last log (1.3 to 4.8 h old) and none has a `4_1_cts` log. D22 applied at 05:0x with the tail split on 1 of 16 PV types (R, KV-D23-REACH: `re.fullmatch("^kv3_pv")`).
7. Closed since 03:20 (R): hd_serdes sd9he signed (TT -27.16, hold 0); svc hslice signed twice (mm3r at 30 ps with r692; mm4 by r708 re-sign, TT +184.88); lep_pair vE28 signed and in HEAD r2; t25 stride-2 pilot GRT 1,022 -> 0.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Take the 1,140 ROM-loop rows out of D8e before publish; close those hops by core placement; ECO the routed col_h9_r2 as the family pilot | col 215 | S81-DIE-R3, FABLE-FIX-S81-BANKLEAF, S81-COLGEN-1 |
| 2 | S81 | D8e leaf rows (XR, core reset relays, face stride): judge the first kits at the TT gate; open a lane item for the interior M6/M8 window class | leaf 75, kv_leaf 5 | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 3 | QC | Measured-hold bind per clock root instead of an error at `ncl != 1` | sc 9, su 5, fe 5, fw 10 as an upper bound; 5 kits proven | WAVE-FLOW-R2, QC-TYPES-R3 |
| 4 | KV | D23 with `kv3_pv.*`, bands sized by `band_capacity`, reset hops; read hg/hgi at CTS now | pv 16; first evidence for hg/hgi 19 | FABLE-FIX-KV-HG |
| 5 | QC | N4 then N4.1 on one measured st_a kit; cbn/cbf/cbx place errors | st_a 11; cb 18 | QC-PLAN-R3, FABLE-FIX-QC-N, QC-TYPES-R3 |
| 6 | S81 | Serdes: H18 is the first rail-clean kit; the die pad-clock trunk to the moved `io_pma_rck` pin has no plan field | serdes 11 | FABLE-FIX-S81-SERDES2, S81-DIE-R3 |
| 7 | HEAD | hd_mesh: balance the 5 short taps before hold padding; first hd_lep0N build on r2 | 2 types, then the die | FABLE-DIE-HEAD, FABLE-FIX-HEAD-LEP0N |
| 8 | S81 | svc mergex at 30 ps + r692 (the hslice recipe); r708 re-sign of mergex_mm3b | 1 core, then svc 16 | FABLE-FIX-S81-SVC2, NOMCAP-1118 |

### Lever 1. S81 col: remove the ROM-loop relay rows, close col_h9_r2 by ECO

**Evidence (V).** `d8e_rd.json` rows by class: ROM `addr_in` 480 and `ce_in` 480 (168 types, 420 to 640 um), `u_s*.q*` 180 (144 types, 420 to 692 um), `u_t*.c*` 288, `u_n*.fi` 180, `u_n*.a` 96, `u_e*.xb_data` 72, y_cc / y_x links 126 (920 to 1,244 um). The die bind on this plan is running on epyc8 (`bind.py elab ... --strict`). Routed col_h9_r2 numbers as in headline 2; its `config.mk` has `OT_HOLD_FF_MARGIN = 0` and the SDC hold uncertainty is 25 ps.

**Root cause.** The relay generator treats every hop over 405 um as a schedulable link. The cfg7 sequencer loop is not a link: its read latency is fixed in RTL. The frame tracer models the sequencer as a 0-edge pass-through, so the only signal is `RELAY_DEPTH_UNSCHEDULED`, which D8e plans to name in the ack record and pass.

**Fix.**
1. S81-DIE-R3: do not publish D8e with the 1,140 rows. Filter `inst ~ u_c<b>_<k>` with port `addr_in` / `ce_in` and `inst ~ u_s<n>` with port `q<k>` out of `relay_depth` and rebind as the delta; the other 918 rows stay only where the tracer can schedule them (R: BANKLEAF is adding that).
2. FABLE-FIX-S81-BANKLEAF: the ROM hops are 15 to 235 um over reach, so move the ROM cores toward the sequencer (0 cycles), as already started. Deliver as one col row set for all 168 types.
3. S81-TYPES-R3 + CAPSKEW-ECO: col_h9_r2 pv11b6518d is 4.87 ps and 5 hold ends from the gate. Name the 2 DRCs and the 102 unconstrained ends, then run the capture-skew / hold-pad ECO on the routed DB (the sd9he form: 15 flops, 113 pads). A signed r2 proves the family without relay rows; 50 placed col kits are waiting on the same answer.
4. P: the macro-to-macro worst path means the r2 TT miss is set by core pin timing plus distance, so core placement also closes TT; do not add a cycle there before the placement rows are measured.

### Lever 2. S81 leaf: D8e rows, TT-gate reads, interior congestion class

**Evidence (V).** TT gate estimate against the FF-session report, same DB:

| type | CTS wns | TT gate | `5_global_route.rpt` |
|---|---|---|---|
| t11 | -304.64 | -288.97 | -5.30 |
| t15 | -401.81 | -350.29 | -17.59 |
| t30 | -283.77 | -315.26 | -29.06 |
| t44 | -160.55 | -288.41 | -11.32 |
| t54 | -575.04 | -470.52 | -30.37 |
| t55 | -384.19 | -449.57 | -30.27 |
| kv_leaf t4 | -273.55 | -259.65 | -4.71 |
| kv_leaf t5 | -403.50 | -297.36 | -34.49 |
| t50 | -684.45 | -445.36 | -94.32 |
| t27 | -610.56 | -515.04 | -202.02 |
| t38 | -488.12 | -462.95 | -248.26 |
| t16 | -734.41 | -733.84 | -384.76 |
| t53 | -1,085.45 | -891.61 | -666.38 |

All these kits: `VERILOG_DEFINES = -DSYNTHESIS` (no XR), plan before D8e. GRT overflow rows: t24 18,328, t25__cl55642d17 99,680 (still running), t68 15,143, t40__clf8bbdae1 10,497, t4 2,283, t41 1,620, t25__cl431c660f 1,022, t29 547, t35 4 (GRT-0232). Seven more leaf kits stop at place on `OT_VPW_BANK distance exceeds 100um` (t1 t10 t13 t14 t75 class); kv_leaf t1 and t3 on PLACE-HPWL 1.48 x and 1.32 x.

**Root cause.** Unchanged from 03:20 for timing (VS core clk-to-`x_wa` 383 ps, reset relay far from the core pin). For the interior class: one window of 50 to 150 um carrying only horizontal-layer overflow is a bundle crossing one channel, not pin access. P: the FIRM bank placement pulls the write bus of one VPW bank through a single gap between hard cores. Not shown; the stage DBs were cleaned.

**Fix.**
1. S81-DIE-R3: D8e keeps XR 16/16, the 1,967 reset relay sites and `face_flop_ns_types` stride 2 (R, all in). These do not depend on the col rows; if the col delta costs a rebind, publish the leaf rows first.
2. FABLE-FIX-S81-STRIP: read the first XR kits at `postcts_gate_tt.json` and `tt_setup_repair_grt.log` only. Expected (P): the `wdo_q` class gains one cycle of 833 ps against misses of 260 to 734, so t16 and t53 (-734, -892) may keep a residue; take their class table first.
3. FABLE-FIX-S81-STRIP: keep `5_1_grt.odb` on t24, t68, t25__cl55642d17 and t40 and image the window. If it is a core gap, the fix is a bank or core move in the type rows, not stride.
4. The `OT_VPW_BANK distance exceeds 100um` stop is a placement check on a path that XR re-times; with XR in, it should be measured again before any site work.

### Lever 3. QC measured-hold bind with forwarded clocks

**Evidence (V).** epyc9 `s29q103S4Q9N3/items/sle_sc_v3/attempt_2`, `5_1_grt.log` line 727 after `OT_HOLD_BUDGET added 0 ... hold_ws -21.86 ... OK`: `OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples 8205 missing 0 clocks 3)`. `vclk_measured_hold.tcl`: `ot_vmh_pinreg_mean` maps a clock to its root only when `fwd_roots` is non-empty and `ot_cf_root` exists; the bind then requires exactly one clock name. The col sign-off record shows the working form: `samples 1496 missing 0 clocks 1 forwarded_excluded 8`.

**Root cause.** In these QC kits the pin registers are clocked by forwarded cland clocks that are not in the kit's forwarded-root table, so they count as separate clocks and the step aborts. All samples have arrivals (`missing 0`); only the clock count fails.

**Fix (WAVE-FLOW-R2 with QC-TYPES-R3).** Bind the IO virtual clock from the pin registers of the primary clock and exclude forwarded-clock registers, as sign-off already does (`forwarded_excluded`), or fill `fwd_roots` from the plan cland rows at gen. Then relaunch the five kits from GRT; three of them are at CTS wns 0.00, -5.29 and -33.43. The same error stopped HEAD sd9c on 11-16 (R), so the fix is die-agnostic.

### Lever 4. KV D23

**Evidence.** V: 4 PV kits stop at `OT_CLAND no legal nonoverlapping row/site in reserved band` (pv_v2 and pv_v4 `u_cland_raw_fs_o_pvw...`, pv_v6 `..._valid_d1_0`, pv_v2n `u_cland_fstart_ft26_o`); hub_C 773,818 and hub_Wo 406,241 cells; no KV kit past placement. R: D22 gate of record passed (strict bind 0 errors, R8 recheck 0, LATCHECK 2,404 / 2,404); not in D22: rider (29 routed hops over 405 um), reset relay rule, `u_d` pipes, pc taps, hub splits; hub_Wi shell 299,999 cells with 14 hard `qkd_hr` masters; hub_C split gate A failed 16 EMIT (reset_net on ring rows, `landing_ring_wreg`), gate B running, 1 collision with a reserved die clock rect open.

**Fix (FABLE-FIX-KV-HG).**
1. D23 in one event: `types ["kv3_pv.*"]`, writer-start and raw-reset bands grown from `band_capacity.py measure` on all 16 PV types, rider, reset hops, hub_Wi rows. hub_C follows when gate B and the clock-rect collision are clean; do not hold D23 for it.
2. hg / hgi / pc / hroot / io_cor (25 kits placed on HG6) are not touched by the PV rows; under r710 they survive the apply. Their first CTS tap-balance and wns lines are the first KV evidence; read them before composing D24.
3. D24 (lighter rings) should be decided from the 186,960 ring cells in the hub_Wi shell and a measured ring kit, not before.

### Lever 5. QC N4 / N4.1 and the cb types

**Evidence (R unless marked).** N4 chain running (group A stations, coll_core 43 taps, clk_t115 split, relay_sites for 11 st_a types). N4.1 by FABLE-FIX-QC-N: u_btab bank moves tested (0 halo hits, lane latency equal), rs_s per-row copies, nb_od / nb_oc station (+1 on x_fe_o), cland forwarded-clock insertion target 485 instead of 419 ps for three masters with setup over 80 ps; one kit to routed sign-off, first CTS in about 3 h. V: cbx_q10__cl94a12200 stops at `global_place.tcl ... can't read "nka_blk": no such variable`; cbf_q01_s2 and cbn_q11__cl5cc92dfe at `GRTM mode edge_outline`; st_b refused at 486,894 to 501,829 cells; tt_ctlm TT gate -258.47.

**Fix.**
1. QC-PLAN-R3: apply N4 as composed. FABLE-FIX-QC-N: no N4.1 rows before the single kit is read at CTS.
2. QC-TYPES-R3: the `nka_blk` Tcl error is an unset variable in the generated `global_place.tcl` (V: the error line; P: a gen branch for the nk_a hard-core form that this type does not take). Fix in gen; P: it stops every cb type built with that core form, so check cbn / cbf kits for the same line.
3. The +66 ps forwarded-clock target is a contract change on the sender; check the three cland masters in the signed fe / hc kits before it becomes a gen default.
4. tt_ctlm still needs the RTL stage (flat `u_core`, 253 ps wire + 700 ps logic, R).

### Lever 6. S81 serdes

**Evidence (R, SERDES2 / DIE-R3).** H18 (H17 recipe + `OT_S81_LPL_CHUNK`, PHY row cut): rail check 6,726 rows 0 bad (H17: 2,046 of 6,664 bad), in placement at 04:41. H17 with nominal clock cap: TT -69.66, internal hold -15.88 / 20 ends. D8e: u_cmem read register at 0 cycles, TAP-GROUP-CAP-1 back (cap 1,700; t13 clk_t42 split in 4), `io_pma_rck` pin moved x 332.704 -> 1,448.032 on 5 shore types (insertion 1,695 against 2,217 ps). Open: the die pad-clock trunk (about 1,115 um, 3 hops) has no plan schema field, and `serdes_shore_delta.py` would move the pin back.

**Fix.**
1. S81-DIE-R3: add the trunk as explicit die clock rows (three stations <= 405 um on M8/M9) in the clock event, and make `serdes_shore_delta.py` read the pin from the plan. Without it the type closes against a pin the die cannot feed.
2. FABLE-FIX-S81-SERDES2: sign H18 under r708 if routed TT >= -42; otherwise the sd9he ECO form (capture skew + hold pads) on the routed DB. The six non-shore types wait for the H18 result, not for a new H form.

### Lever 7. HEAD

**Evidence (R, FABLE-DIE-HEAD 04:18).** hd_mesh mesh_w1 with the credit counter on one tap: TT at CTS -0.96 (was -50.56). Hold before repair: cross-tap 10,190 ends at -185.30, same-tap 1,408 at -84.24; five taps short of the 450 ps target (clk_t45 322, clk_t54 330, clk 332, clk_t42 360, clk_t43 384). The earlier attempt lost TT -49.56 -> -68.34 after 37,912 hold cells. V: no hd_lep0N kit directory exists on epyc9 / epyc10 / intel1 under event `..._r2` at 05:45; hd_tile on NF15f a4 reads TT gate -354.59 (it is signed from nf15c_tp2_land1).

**Fix.**
1. FABLE-DIE-HEAD: the 128 ps tap spread is the hold demand. Fix the five short taps (delay cells at the tap root, or the tap group rule) and re-run CTS before pre-GRT padding; padding 10 k ends by 185 ps repeats the 37,912-cell run.
2. FABLE-FIX-HEAD-LEP0N: first r2 synth, band and CTS read; nothing technical can be said before it.
3. M8 grant: 1,723 die-track conflicts on signed types (hd_tile 1,069) stay a die clock leg move (R). It blocks die assembly, not the type count.

### Lever 8. S81 svc mergex

**Evidence (R).** hslice: 15 ps finished at FF r2r -0.00 (not signed), 30 ps + r692 signed (+12.14 routed), 50 ps failed on utilisation. mergex mm6 in GRT, mm3r and mm15r in CTS hold repair; mergex_mm3b routed r2r -6.93, r708 re-sign running (hslice_mm3b re-sign: FF -2.85, not signed).

**Fix.** FABLE-FIX-S81-SVC2: mergex_mm3r is the form of record; stop mm15r (hslice proved 15 ps leaves no room). If the mm3b re-sign lands within 3 ps as hslice_mm3b did, close it with the r583 internal hold ECO instead of waiting for the rebuild.

## 2. Die floorplan or type-internal, per die

| die | unsigned families | where the blocker sits | one die-level change |
|---|---|---|---|
| S81 | leaf 75 + kv_leaf 5 | Type structure, fixed by die-plan rows (XR stage, reset relay sites, face stride). A second, type-internal class: interior M6/M8 windows on 4 types | D8e |
| S81 | col 215 | Type-internal and close (routed -46.87, 5 hold ends). Held by plan rows: relay hops over 405 um and bank-leaf core distance | D8e col delta without the ROM-loop rows, with core moves |
| S81 | serdes 11 | Type-internal (rck tree, PG rails) plus one die item: pad-clock trunk to the moved pin | D8e rows + die clock rows |
| S81 | svc 16, dsdv_slice 20, slice_station 5, singles 5 | Type-internal (mergex core hold; kit preflight / `edge_outline`; slice_station t6 TT gate -229). Not opened this round beyond the wave rows | none |
| HEAD | hd_mesh | Type-internal (tap balance, cross-tap hold) | none |
| HEAD | hd_lep0N | Die plan (bands, pair views, tap offsets): delivered in r2, unbuilt | r2, already applied |
| QC | sc, su, fe, fw (29 unsigned) | Flow: measured-hold bind; no floorplan cause found | none; lever 3 |
| QC | st_a 11 | Die plan rows inside the type (stations, tail copies, bank sites) | N4 + N4.1 |
| QC | st_b 12, hc 11 | Type size (350 to 502 k cells) and routed hold; not floorplan | none |
| QC | cbn / cbf / cbx 18, ctl 7, tt_ctlm | Generator and RTL (place Tcl error, `edge_outline`, missing stage) | none |
| KV | pv 16, pc 6 | Die plan rows (tail split, bands, taps) | D23 |
| KV | hub 5 | Partition size: split on signed ring and host masters | D23 (Wi), later hub_C |
| KV | hg 8, hgi 11, others 4 | Unknown: no CTS number exists | none known |

No die has a die-floorplan routing problem: die GRT overflow is 0 on S81 (M4 to M7 use under 5 %), QC (worst cut 0.237) and HEAD combo (0.37 %) (R, FABLE-DIE-* 11-17). The die-level open items are clock structure (S81 K table from B6gsh, 93,626 unreserved clock cell sites, 21 legs over 405 um; HEAD M8 grant) and they gate die STA, not type sign-off.

Answer: S81 yes, one event. D8e plus a corrected col delta reaches 306 of the 352 unsigned types (leaf 80, col 215, serdes 11). KV yes for 22 of 50 (D23: pv, pc), unknown for hg / hgi. QC no: N4 covers 11 of 106; the widest single change is the flow fix of lever 3. HEAD no: one type each.

## 3. Stop list (the 03:20 list stands, plus these)

1. Do not publish D8e with `relay_depth` rows on `u_c*_*.addr_in / ce_in` or `u_s*.q*`. Do not record `RELAY_DEPTH_UNSCHEDULED` as an accepted finding for those rows.
2. Do not read `5_global_route.rpt` / `6_finish.rpt` wns as the TT result; it is the FF session. TT is `postcts_gate_tt.json`, `tt_setup_repair*.log` and sign-off.
3. No relaunch of pre-D8e leaf kits; no SETUP_TRIAGE threshold change (the 8 kits that look closed at GRT are at -260 to -470 TT).
4. No row stride as the answer to t24 / t68 / t25__cl55642d17 / t40; no S81-wide stride default (fires on 387 of 395 types, R).
5. QC: no relaunch of sc / su / fe / fw kits with forwarded-clock pin registers before the bind fix; no N4.1 plan rows before its one kit is measured.
6. KV: no judgement of PV on HG6 or D22 kits (split covers 1 type); no D24 compose before one KV CTS number; no hold of D23 for hub_C.
7. hd_mesh: no hold padding against a 128 ps tap spread.
8. svc: no 15 ps and no 50 ps margin builds.
9. Serdes: no `serdes_shore_delta.py` rerun on D8e; no export of H17 (rail defect).

## 4. Not checked

- The D8e bind output itself (still running); whether S81-DIE-R3 acted on the BANKLEAF alert after 05:08.
- The BANKLEAF verilator result, the 515 bank-leaf paths and the core-move rows (R).
- What the interior congestion windows contain (no stage DB; the cause in lever 2 is a proposal).
- Whether the five QC kits pass sign-off once the bind is fixed; how many of the 29 sc / su / fe / fw types carry forwarded-clock pin registers.
- Any KV timing. Any hd_lep0N r2 result. H18 beyond the 04:41 post. mergex results.
- dsdv_slice (20), svc shell types and bk_sel / eng / gunit / iqf / seqhost: wave rows only.
- QC N4 bind result; the cland +66 ps effect on port hold.
- Die STA on the real clock for S81 and HEAD (0 measured hold pairs, R).

---

# FABLE-CLOSURE-STRATEGY 2026-11-18 03:20 PST (0320): delta on 23:20

Reviewer: FABLE-CLOSURE-STRATEGY-0320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (03:14 to 03:40 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
All lanes were stopped 00:30 to 03:10; most "running" items below are builds that kept going with no reader.

## 0. Headline

1. **S81 strip leaves: 14 of the first 21 route verdicts are a pre-route setup stop of -244 to -734 ps, and it is structure, not settings (V).** Worst classes in the kits: VS core `x_wa` -> `u_vp_g_wr1_u_w.wdo_q` (t16 -715 / 1,025 ends; t50 -684 at CTS), and reset into hard-core `rst_n` pins (`u_vsw/rst_n` -298 to -425 on t15 t26 t38 t50). The XR stage that was decided for this family on 11-17 is not in any of these kits (t50: 0 `ot_s81sl_xr` instances, `VERILOG_DEFINES = -DSYNTHESIS`). The other 7 verdicts are GRT congestion (t25 class).
2. **The GRT optimism is a serdes rck-tree problem on both dies, not a fleet problem (V).** hd_serdes, three forms routed overnight: sd9h GRT TT -0.24 -> routed -45.34; sd9pa -10.89 -> -49.62; sd9pb2 -0.89 -> -92.27. Over 85 other kits with both a `grt_policy.json` and a later `signoff.json` (epyc7/9/10), TT moves mostly within +-25 ps and FF hold within +-10 ps; the bad outliers are QC sle_fe_v3 (+39 -> -29), S81 col_h9_r2 (-19 -> -47) and QC slw_hc1 (-14 -> -41).
3. **hd_serdes sd9h is 3.3 ps from the gate (V):** DRC 0, TT -45.34 / 119 ends, FF hold -31.02 / 169 ends. sd9pa: DRC 0, TT -49.62 / 8 ends. Both are ECO-sized on setup.
4. **lep_pair vE28 is 12 flops from sign-off (V):** DRC 0, TT -0.66, internal FF hold -9.7 on 12 ends (the other 2,739 hold ends start at ports). No ECO has been started on it. It is the only thing hd_lep0N waits for.
5. **KV D22s failed its strict bind at 23:58 (V); this is the third D22 plan.** `R8_STRAP_PAD kv3_pc_v1__cl7f648944 slg.vreq: pad 18 > strap capacity 15`, `TYPE_SPLIT` 12 instances -> 7 variants, `EMIT clock landing`; R8 recheck 64 unequal groups, 2 inversions. Rider gate3: 30 `R8_STALE`, LATCHECK 2,404 / 2,404. Meanwhile the wave ran PV kits on KV-HG6 with no tail copies (pv_v6: 0 `ot_dp_dly_keep`), and 4 of them tripped the CLAND band breaker.
6. **The svc hold misses are not ECO-sized (R, SVC2 03:14).** hslice_mm4 ECO failed (1,092 negative ends, incremental route failed); mergex_mm3b refused (1,567 ends); hslice_mm7 at 50 ps died at CTS (53,294 hold buffers, utilisation over 100 %). My 23:20 lever 4 item 1 was wrong for these two cores. V: hslice_mm6 is in detailed route (471 violations in the current iteration), mergex_mm6 in CTS hold repair at 30.9 k buffers.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Strip leaf: XR stage on the VS -> VPW write, registered reset at the core `rst_n` pins, in one plan/RTL event | 14 stopped strip types now; the same class sits in all 75 leaves | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 2 | HEAD | lep_pair vE28 hold ECO (12 ends) -> sign -> view pack -> hd_lep0N | hd_lep0N, then the HEAD die | FABLE-FIX-HEAD-LEP0N, HEAD-PLAN-R4 |
| 3 | HEAD, S81 | Serdes rck: close sd9h / sd9pa by post-route clock ECO; size rck pads on extracted arrivals; never decide these types at GRT | hd_serdes; 11 S81 serdes types | FABLE-FIX-HEAD-SD9F, FABLE-FIX-S81-SERDES2, CAPSKEW-ECO |
| 4 | KV | D22: fix the `slg.vreq` pad (18 > 15) before a fourth bind; regenerate the rider R8 table from that bind; PV bands by `band_capacity`; hold PV kits | PV 16, pc 6, the die event | FABLE-FIX-KV-HG, KV-R3 |
| 5 | S81 | Strip south-face pin-row congestion (t25 class, 7 types) and col relay reach, as generator rules | 7 strip types; col 216 | FABLE-FIX-S81-STRIP, S81-TYPES-R3 |
| 6 | QC | N4 with flt_bank stations + sited tail copies; own tt_ctlm | st_a 11 types; tt_ctlm types | QC-PLAN-R3, TAIL-REPL |
| 7 | S81 | svc hslice / mergex: sign mm6 if it passes; if not, cut the hold demand at its source instead of adding buffers | 2 cores, then the svc shell | FABLE-FIX-S81-SVC2 |
| 8 | KV | Hub types over the size OpenROAD closes: split hub_C and hub_Wi on signed ring cores; waive hub_Wo | 3 hub types | KV-HUBWO-SPLIT rows, FABLE-FIX-KV-HG |

### Lever 1. S81 strip leaf: the stops are two structural paths

**Evidence (V).**
- `kit_wave_stages.tsv`, current plan, strip route rows: 14 `FAIL_POSTCTS SETUP_TRIAGE` (iqf__t1 -537, kv_leaf t4 -260, t11 -289, t15 -350, t16 -734, t26 -483, t27 -515, t30 -315, t38 -463, t44 -288, t50 -445, t54 -471, t55 -450; last one t55 at 02:55), 7 GRT congestion (t25 t29 t35 t4 t40 t41 t68), t51 DPL-0033.
- epyc8 `.../items/ot_s81sl_leaf__t50/attempt_7`, `4_cts_final.rpt`: wns -684.45, tns -336,321. Path `u_bound.u_u_vs/clk` -> `x_wa[0]` leaves the core at 401.7 ps, then 38 cells (31 buffers, 7 gates) in three long hops (401 -> 911, 951 -> 1,288, 1,351 -> 1,576) to `wdo_q[0][82]`, arrival 1,603 against 919 required.
- Same kit: `OT_VPW_BANK placed 317 FFs FIRM, nearest-bank max 11.328um`. So the bank placement works and does not close the path: the capture flops sit at the bank, the source core and the arbiter logic do not.
- Same kit: asynchronous group, `u_lpad_leafdn_i0.q[0]` -> 22 buffers -> recovery at a `_DFF_PN0_`, -41.42.
- `tt_setup_repair_grt.log` last line per kit: t16 -714.4 `wdo_q`; t15 -297.8, t26 -329.4, t38 -420.2, t50 -424.7 all `u_*vsw/rst_n`; kv_leaf t4 -243.4 `u_vp_g_ln_7_u_l/rst_n`; t55 -291.1 `g_u_lf4_u_vp_cf.native_memory`. t16 then crashes: `[ERROR RSZ-0074] Failed to build tree from global routes`.
- All these kits: `OT_HOLD_FF_MARGIN = 0` (plan 30c40fae, before the D8d key).

**Root cause.** The VS core spends 383 ps clk-to-`x_wa` inside the core (R, 11-16 review; V 401.7 at the pin). The five-writer arbiter then has about 430 ps for 400 to 1,000 um of wire plus 7 gates. No placement can close that. The reset class is the same shape: a relay flop far from the core pin it drives. The repair cannot help either path and spends its time (and crashes) trying.

**Fix.**
1. S81-DIE-R3 + FABLE-FIX-S81-STRIP: put the XR form (r432 `ot_s81sl_xr`, +1 cycle on `x_w` and `x_wd` together, pre-approved) into the next S81 event for every leaf type, with bank placement kept. I did not find XR in D8d (P: it is not there; the 03:13 D8d result does not name it). If D8d is already bound, make it D8e, not a per-type patch.
2. Reset: one `ot_dp_rrelay` stage sited within 50 um of each hard-core `rst_n` pin (vsw, vp_g_ln), from the existing relay-site rows; the 64-cycle reset hold makes the cycle free.
3. FABLE-FIX-S81-STRIP: class table of the 14 kits from `4_cts_final.rpt` (not from the gate estimate) before anything is relaunched. t15 shows kit GRT -17.6 against an estimate of -350 (R); find what the estimate adds, but that question does not change t16 / t50, which are real at CTS.
4. WAVE-FLOW-R2: `tt_setup_repair.tcl` must catch RSZ-0074 and keep the pre-repair DB; today the crash hides the real number.

### Lever 2. HEAD: sign lep_pair vE28 by ECO

**Evidence (V).** epyc9 `head-lep0n-opus/lep_ve28/kit/ot_s81hd_lep_pair_kit/signoff/signoff.json` (23:27): NOT SIGNED, DRC 0, antenna and PG PASS, `setup_tt -0.66 / 1`, `hold_ff -177.0 / 2751` of which `std_min_start.port 2739`, `nonport_n 12`, `nonport_wns -9.7`. TT insertion 517 to 528 ps; pair skew min 87.3. No ECO directory exists in the kit. hd_lep0N p2 (diagnostic, old windows) is at CTS wns -379.62, tns -97,009: not a verdict.

**Fix.**
1. FABLE-FIX-HEAD-LEP0N: `hold_eco_internal_run.py` (r583) with the top-layer route fix b6e97307 on the routed vE28 DB now; hei3 closed 7 -> 0 pads in three rounds the same way. Sign, export.
2. HEAD-PLAN-R4: one pack = vE28 views (`bb.v` KCRED 28) + plan_grown2 bands + related-pair windows; take the four pair tap offsets from the signed core's `clock_contract.json` (insertion about 527, not the 450 target).
3. M8 grant (R): track-level lock 4,321 -> 3,178; hd_tile (signed) 1,069. Types do not re-sign; if the shape test shows real overlap the die clock legs move. Still open with FABLE-DIE-HEAD.
4. hd_mesh `mesh_w1` (related windows) is in CTS (V 03:20); read its cross-tap hold class against 11,732 ends / -125.74.

### Lever 3. Serdes rck trees: decide on extraction, close by clock ECO

**Evidence.**
- S81 H17 (R census; V the eight census files exist, epyc9 `fable-fix-s81-serdes2/drtx/census/`): GRT -27.17 / +0.12, routed -117.47 / -55.85; data nets median -14 ps; rck sinks spread 1,848 to 2,051 routed; lpl_r.rc -> o 144 ps, lpl_2_w.wc -> b 179 ps.
- HEAD hd_serdes (V, epyc10 `fable-fix-head-sd9h/<form>/hd_serdes/{grt_policy.json,signoff_fable/signoff.json}`):

| form | GRT TT / ends | routed TT / ends | GRT FF hold | routed FF hold / ends | DRC |
|---|---|---|---|---|---|
| sd9h (PW16 + PW8) | -0.24 / 1 | -45.34 / 119 | -24.34 | -31.02 / 169 | 0 |
| sd9pa (PPCYC) | -10.89 / 1 | -49.62 / 8 | -17.77 | -33.68 / 432 | 0 |
| sd9pb2 (SPCYC) | -0.89 / 2 | -92.27 / 228 | -35.12 | -46.66 / 107 | 0 |
| sd9pc2 (both) | +0.67 / 0 | none: `DRT-0255` | -21.12 | none | - |

- sd9h vclk reference latency 488.8 at GRT, 446.4 routed: the tree is 42 ps faster under extraction, as on H17 (74 to 94).
- Fleet (V, 85 kit pairs): the effect is small elsewhere. HEAD types (insertion 478 to 521) move TT by -9 to +11 typically; S81 slice_station (280 to 350) by -44 to +90; QC by -68 to +61.

**Root cause.** The rck balance pads are sized on placement RC and confirmed on GRT RC. A 2 ns, 63-stage tree turns a few percent of clock RC error into 50 to 180 ps between branches (R, SERDES2). Ordinary CTS trees of 300 to 520 ps do not show it.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h needs 3.3 ps on 119 ends; sd9pa needs 7.6 ps on 8 ends. Run `capskew_eco_run.py` on both routed DBs, then the internal hold ECO. The 100-pad hold limit will refuse 169 / 432 ends: split by rck branch and run two rounds rather than raise the limit blind. First to pass signs. sd9pb2 is out.
2. I withdraw my 23:20 line "stop PPCYC/SPCYC once sd9h shows TT >= -42 at GRT". No rck-tree type is decided at GRT.
3. CAPSKEW-ECO + WAVE-FLOW-R2: for kits with `OT_S81_RCK_BALANCE` (S81 serdes 11, hd_serdes), make the flow: route -> extract -> rck pad re-size on SPEF sink arrivals -> incremental route -> hold ECO. The GRT policy stays as a triage only.
4. FABLE-FIX-S81-SERDES2 / S81-DIE-R3 (R, agreed): cmem read register, centre-root trunk, t42 four-tap split in the S81 event; pilot t13 only after that.
5. sd9pc2: `DRT-0255` is the M6 pair-row class; hd_serdes kits need the `pg_row_guides.tcl` hook (r598) that S81 serdes has. Do not rerun unchanged.
6. Triage margin elsewhere (P): a type with GRT TT between -42 and +30 is not safe; plan the CAPSKEW ECO for it rather than a rebuild (col_h9_r2, slw_hc1, sle_fe_v3 are this case).

### Lever 4. KV D22

**Evidence (V).** epyc7 `kv-hg-opus/d22s/gate/gate.out` (07:58Z): PRE PASS, G0 PASS (0 errors, 2,403 warnings), `RC_BIND 1` with 3 errors as in headline 5, `RC_R8CHECK 1`, LATCHECK not run (no `*_bound_top.sv`). `kv-pv-rider/gate3/gate.out`: `BIND_ERRORS 30 {'R8_STALE': 30}` (`pvw_0__u_T0Q0_45_r0.b as-built 2 bound 9, table ... bound 5`), LATCHECK PASS. Wave 01:37 to 01:48: `OT_CLAND no legal nonoverlapping row/site in reserved band` for `u_cland_fstart_ft0_o` (pv_v6), `ft26_o` (pv_v2, pv_v2n), `u_cland_raw_fs_o_pvw...` (pv_v4, literal-local-reset). Sited proof epyc9 `kv-hg-opus-site/proof/kv3_pv_v12`: placed; `OT_TAIL_SITE copies 7009 of 7040 sited ... max_hop 441.3 um over_380 1205 core_crossing 0 in_halo 0`; no timing number yet.

**Root cause.** The pc `slg.vreq` pad needs depth 18 and the R8 strap carries 15, so instances of one type bind differently and the emit inventory changes. The rider's R8 table was built from an older bind. The PV writer-start bands are sized for the pre-split flop count.

**Fix (FABLE-FIX-KV-HG).**
1. One plan station on `slg.vreq` for pc_EN / pc_ES so no pad exceeds 15 (or a 5-bit strap for that bus only). Then the bind; G0 cannot see this class, so do not compose again before it.
2. Rebuild the rider R8 table from the passing bind; R8_STALE is a stale input, not a design error.
3. Run `band_capacity.py measure` (r681, all dies) on the 16 PV types and grow the writer-start and raw-reset bands in the same plan (HEAD needed 11 rects).
4. Hold all `^kv3_pv` items on KV-HG6: they have no tail copies, so their timing is the unsplit -1,197 class and 4 already fail the band.
5. Sited proof: read CTS reg-to-core on pv_v12. The 1,205 copies over 380 um need one more stage (K+1) in D22; decide that from the CTS number, not before.

### Lever 5. S81 generator rules: face pin row and relay reach

**Evidence.** Strip (R, STRIP 03:4x; V the 7 GRT rows): t25 has 595 `leafdn_i0` input regs in 12 full rows at y 4.32 to 7.29 on 598 pins in 124 um; 101 congested gcells at x 360 to 480, y 0 to 7; M6 568 + M8 347. Pilot `t25_ns2` (row stride 2) is running. Col (R, S81-TYPES-R3 23:21): poly relay hops 446 to 746 um in every col family (limit 405); col_h9_r0_p2 stops on 2 unfitted groups (252 / 206 um). 22 direct wires of 412 to 640 um (R, COORD brief; I found no generator post). Col after the marker fix (V): 10 rows running, none past place yet, 87 old place FAIL rows; col_h9_r2 reached sign-off with DRC 2, TT -46.87, hold_ff -62.46, `unconstrained` FAIL.

**Fix.**
1. FABLE-FIX-S81-STRIP: if `t25_ns2` gives GRT 0, make the stride a generator default from pins/um on the face window (no per-type plan rows), and apply to the 6 other types in one relaunch. t29 is the landing-ring variant (`cland_strip_rows`).
2. S81-TYPES-R3: gate `OT_RELAY_POLY` max hop over 405 um at generation, and insert stations so every poly hop is <= 405 um (+1 cycle each). The 22 direct wires get the same rule. Otherwise all 216 col types pass place and stop at CTS.
3. col_h9_r2: name the 2 DRCs and the unconstrained endpoints first; the 4.9 ps of TT is a CAPSKEW case.

### Lever 6. QC N4

**Evidence.** (R, TAIL-REPL 23:19; V the keep kit exists on epyc9) st_a split + keep + sited: CTS wns -901.4 -> -580.7, tns -160,939 -> -123,092; `rs_n_c_p` gone; new worst `u_r2.flt_bank_o -> u_r0.flt_bank_i` (819 to 1,000 um, R). (R, QC-PLAN-R3 03:15) N4: flt_bank 2 + 2 stations need `claude/qc-intra-stations-1118` (proof bind running, READY about 05:00); coll_core 43 taps + t115 split composing; tt_ctlm stage unowned.

**Fix.**
1. QC-PLAN-R3: N4 carries tail split + keep + sites, flt_bank stations and the tap rows in one event, as planned. Before the apply, place ONE st_a kit to CTS from the N4 bind and read wns; the acceptance is better than -250 with no path over 380 um unregistered.
2. COORD: tt_ctlm (31 cells in `u_core`, about 253 ps wire + 700 ps logic, R) needs an RTL stage and has no lane; without it those types fail N4 as they failed N3.
3. Routed QC rows already inside TT (V: sle_st_b_v1 +7.0 and -32.3, slw_st_b_v1 -25.4 and +9.5, slw_stm_v3 -4.8, slw_hc1 -41.1): their open item is internal hold; give them the r692 hold repair and the r583 ECO, not a rebuild.

### Lever 7. S81 svc hslice / mergex

**Evidence.** Headline 6. mergex_mm6 CTS hold repair: 36,993 endpoints under margin (R), 30.9 k buffers at +10.6 % area and still running (V).

**Root cause (P).** Tens of thousands of short paths cannot be a skew accident; the cores are built with a 30 ps margin on top of the 25 ps hold uncertainty in the SDC, so the repair is asked for 55 ps on every zero-logic stage.

**Fix (FABLE-FIX-S81-SVC2).**
1. Read hslice_mm6 at route end; sign it if DRC 0 and internal hold >= 0.
2. If mm6 fails: do not go to 50 ps (mm7 proved it does not fit). Check whether sign-off measures internal hold with the 25 ps uncertainty; if it does, build at margin 0 to 10 with r692 (worst + 1 ps floor, bounded re-repair), which removes most of the 30 k buffers and the route pressure that broke the mm4 ECO.
3. Count the endpoints per launch-capture clock-leaf pair in mm4; if a few leaf pairs carry most of the 1,092, a leaf-level clock pad is the ECO, not 1,092 data pads.

### Lever 8. KV hub types

**Evidence (V, wave).** kv3_hub_Wo 406,241 cells, kv3_hub_C 773,818: `OT_NATIVE_CELL_CAP SPLIT-NEEDED`. kv3_hub_Wi: `FAIL_PREFLOOR kit_preflight PROVISIONAL[qkd_hr_core_order, _peer, _prompt, qkd_hr_ingest_eng :routed]` and 1.155 M cells (R).

**Fix.** Waive hub_Wo (1.5 % over; QC signed 351 k and r696 waived 500 k). hub_C and hub_Wi are in the range where every past run failed (0.53 to 1.31 M): split on signed ring masters plus dly cores as KV-HUBWO-SPLIT measured for hub_Wo (rows exist for D23; 419,971 -> 199,876 synth cells). hub_Wi also needs its four qkd_hr cores signed, not routed-provisional. These belong in D23, not in D22.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 03:14 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 (unchanged since 23:10) |
| strip route verdicts | intel2 `autopilot/kit_wave_stages.tsv`; epyc8 / epyc10 / intel1 / epyc2 kits `FAIL_POSTCTS`, `tt_setup_repair_grt.log`, t50 `4_cts_final.rpt`, `config.mk`, `1_synth_odb.v` | lever 1 |
| hd_serdes four forms | epyc10 `fable-fix-head-sd9h/*/hd_serdes/{grt_policy.json,signoff_fable/signoff.json,run_route.log}` | lever 3 table |
| GRT vs routed, 85 kit pairs | epyc7 / epyc9 / epyc10 wave kits, `grt_policy.json` + later `signoff.json` | headline 2 |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/kit/.../signoff/signoff.json` | lever 2 |
| hd_lep0N p2, hd_mesh mesh_w1 | epyc9 `4_cts_final.rpt`; `4_1_cts.tmp.log` | -379.62 at CTS; in CTS |
| KV D22s, rider | epyc7 `kv-hg-opus/d22s/gate/gate.out`, `kv-pv-rider/gate3/gate.out` | lever 4 |
| KV PV kit | epyc7 KV-HG6 `kv3_pv_v6/attempt_5` bound RTL | 0 keep copies |
| KV sited proof | epyc9 `kv-hg-opus-site/proof/kv3_pv_v12/run_place.log` | OT_TAIL_SITE line; placed |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,mergex_mm6}` | DRT; CTS hold repair |
| H17 census | epyc9 `fable-fix-s81-serdes2/drtx/census/` | 8 files present, not re-aggregated |
| VPW marker | intel2 `tree_switch_s81.json` | key gone; last VPW fail 00:32 |

## 3. Stop list (the 23:20 list stands, plus these)

1. S81 strip: no relaunch of the 14 SETUP_TRIAGE types on a plan without the XR stage and the core-pin reset relay. No gate-threshold change for them.
2. Serdes (both dies): no go / no-go from `grt_policy.json`. No new H-form or sd9 route before the clock ECO on the routed DBs in hand.
3. hd_serdes: no sd9pb2 follow-up (-92). No unchanged sd9pc2 route.
4. lep_pair vE28: no rebuild; ECO the routed DB. No hd_lep0N judgement from p2.
5. KV: no fourth D22 compose before the `slg.vreq` pad is 15 or less. No PV kit on KV-HG6. No cell waiver for hub_C or hub_Wi.
6. svc: no hslice or mergex run above 30 ps margin; no post-route data-pad ECO on a DB with more than about 100 negative ends.
7. Col: no mass launch before the 405 um hop rule is in the generator; the first col past place must be read at CTS.

## 4. Not checked

- Whether D8d (plan e291d6a8) carries the XR form or a reset relay at the core pins; lever 1 item 1 assumes not.
- The cause of the t15 estimate gap (-17.6 kit GRT against -350 gate estimate); the endpoint classes of 9 of the 14 strip kits (only last repair lines read).
- Whether sign-off internal hold includes the 25 ps SDC uncertainty (lever 7 rests on it).
- The 2 DRCs and the unconstrained endpoints of col_h9_r2. Any col kit past place. The col direct-wire generator (no post found).
- `t25_ns2` result. hslice_mm6 / mergex_mm6 final results.
- KV: the CLAND band logs themselves (wave lines only); pv_v12 timing after place; band fill numbers for PV.
- QC: every N3 route result beyond the six rows in the GRT/routed table; the N3 clock-chain proof; the intra-station proof bind.
- HEAD: hd_host_e route FAIL (GRT-0116 at 01:48 on NF15f) was not opened; the M8 per-instance shape test; die hold on real views (0 measured pairs on HEAD and S81).
- The H17 census numbers are FABLE-FIX-S81-SERDES2's; I confirmed the files, not the aggregation.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 23:20 PST (2320): delta on 21:20

Reviewer: FABLE-CLOSURE-STRATEGY-2320 (Fable). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round (23:08 to 23:16 PST). **R** = reported by the named lane, not opened. **P** = my proposal or estimate.
Signed (failure_breakdown 23:10): S81 42/394, HEAD 23/26, QC 24/130, KV 6/56. No type signed on S81, QC or KV in the last 4 h (wave stages).

## 0. Headline

1. **S81 col still dies at GPL because the D7w tree-switch marker re-adds the key every tick (V).** `lanes/handoff/tree_switch_s81.json` still holds `OT_S81_VPW_BANK: "1"` at 23:10. Wave stages, last 4 h: 58 col rows FAIL `OT_VPW_BANK needs exactly two real VP SRAM macros, got 0`. The item_env move (6b15cc83) is correct but is overwritten in memory. Until the marker is edited, no col type (216, the largest family on any die) can show a real result.
2. **The S81 die GRT is now real and clean on the clock of record; the landed check still has no result (V).** epyc10 `s81-die-r3-proto/s81/d7w_eco`: ECOv3 clock, taps 21,687, missing 0, overflow 0 / 0 / 0 (M4 2.73 %, M5 4.04, M6 4.42, M7 2.15, M8 0.92, M9 0.79). Then `CHAIN_FAIL CA_CHAIN`: `count_align_plan.py: error: unrecognized arguments: --strap-window --min-lat-cycles 1` (the D7w tree tools predate the r4 recipe). The retry with newer tools (`ca_r4_noparts`) stops at `partition START origins require actual src_part/dst_part on every crossing`. `ca_r4/phase_ocv.log` is empty.
3. **No sited tail-copy result exists yet on either die (V).** KV: the keep + anchor proof (epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12`) sources `tail_copy_anchor.tcl` at `face_flops.tcl:975`, 7,040 rows in `tail_copies.tsv`, but is still in 3_1 GPL (overflow 0.39); no `OT_TAIL_SITE` line yet. QC: `tail-repl-qc-kit/splitk` stops at 1_synth; nobody has placed a sited st_a.
4. **The tail split pushes KV PV over the cell limit (V).** Wave row kv3_pv_v3: `REFUSED: SPLIT-NEEDED: cells 467307 > 400000`. The split adds 19 to 27 k flops per PV type. S81 kv_leaf__t2 is refused the same way (estimate 462,435).
5. **hd_serdes: the structural fix is building (V).** epyc10 `fable-fix-head-sd9h`: `KP4_PW_BENCH PASS`; sd9h `config.mk` carries `ENC_PW16` + `SYN_PW8`, sd9pa carries `ENC_PPCYC`; both are in 3_1 GPL. sd9pb2 and sd9pc2 have a kit and no log yet.
6. **KV D22 is on its third plan (V).** try 2 (`d22gate/gate.out`): PRE FAIL, bind FAIL `pvw_0 column 5 ... flags [(88, 31), (88, 32)]`. Composer plan d22s 957d81e49c52: PRE PASS, G0 0 errors; first bind stopped on a manifest path, second bind started 06:52Z and has not reported.

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Remove `OT_S81_VPW_BANK` from the tree-switch marker; land r676 (skip, nearest bank, FT snap); then read the next col stop classes | col 216 types; leaf t1 t7 t10 t13 t31 t45 t53 t74 t75 | S81-DIE-R3 (marker), FIX-S81-VPW, S81-TYPES-R3 |
| 2 | QC, KV | Sited tail copies, proven at CTS on st_a and pv_v12; PV cell waiver | QC st_a 11 types; KV PV 16 types | TAIL-REPL, FABLE-FIX-KV-HG |
| 3 | HEAD | hd_serdes PW16/PW8; lep_pair vE28 then hd_lep0N with related-pair windows; die clock off the granted M8 tracks | last 3 HEAD types = the die | FABLE-FIX-HEAD-SD9F, FABLE-FIX-HEAD-LEP0N, FABLE-DIE-HEAD, HEAD-PLAN-R4 |
| 4 | all | Close small routed hold misses with the post-route internal hold ECO, not with rebuilds | S81 svc hslice + mergex (then the svc shell, 2 svc families), hd_mesh, QC L2 | CAPSKEW-ECO, FABLE-FIX-S81-SVC2 |
| 5 | KV | D22s bind, with rider + siting folded in; pc 68 taps in D23 | PV 16, pc 6, hroot/pv_v2 band 5 | FABLE-FIX-KV-HG, KV-R3 |
| 6 | S81 | Serdes: H17 routed TT / hold read, then t13 + 10 on D8d | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 7 | S81 | Die landed check on ECOv3 with the r4 recipe; K refresh + clock site reservation as one clock event | die clock verdict; hold windows of every seam type | S81-DIE-R3, FABLE-DIE-S81 |
| 8 | S81 | Leaf and svc place/kit stops: HPWL (t37, kv_leaf t3), landing collectors missing, svc kit_rtl closure, relay_mid coverage | about 25 types | FABLE-FIX-S81-STRIP, S81-TYPES-R3, FABLE-FIX-S81-SVC2 |

QC N4 content (lever 7 of 21:20) is decided and TAKEN by QC-PLAN-R3 (R, 22:51); no new technical finding. QC has produced no N3 kit, so r650, the halo fix and the 40 ps margin are all still unmeasured.

### Lever 1. S81 col: the marker, then the next classes

**Evidence (V).**
- `tree_switch_s81.json`: `OT_S81_VPW_BANK": "1"` present at 23:10.
- Wave stages, last 4 h, S81 place FAIL 81: 58 `VPW_BANK ... got 0` (col), 9 `distance exceeds 100um` (leaf t1 t10 t13 t31 t45 t74 t75), 2 FT off-grid (t7 `82.9376 176.8544`, t53clb `9.3393 1032.3389`).
- Behind it, already visible on col: `OT_HOOK_COVERAGE relay_mid: 2 of 15 stations on the old fallback; unfitted group:even_hop_um u_bound.u_u_r0_u_y_rt_4a_0:252 u_bound.u_u_r0_u_y_rt_4b_0:206` on 4 col_h9_r0_p2 rows (22:45).

**Root cause.** A type-scoped opt-in sits in a die-scoped marker that `apply_tree_switches` re-applies each tick (R, FIX-S81-VPW 23:10; consistent with what I read). The relay_mid stop is a real design class: two relay groups in u_r0 have hops of 252 and 206 um that the even-hop fitter cannot place.

**Fix.**
1. S81-DIE-R3: re-write the marker without the key (`apply_reviewed_tree_marker`). Release hold `s81-col-vpw-1117` only after one regenerated col spec shows no key.
2. FIX-S81-VPW: r676 (`claude/fix-s81-vpw-ftsnap` @0d4134418d4, gate 67/67) reaches kits only through the S81 tools refresh, which r685 unblocks. Then relaunch t7, t10, t45, t53, t74, t75. Do not wait for the B4 plan row; the gen snap covers t7 and t53.
3. S81-TYPES-R3: for col_h9_r0_p2, add one relay station to each of `y_rt_4a` and `y_rt_4b` (252 -> 2 x 126, 206 -> 2 x 103; +1 cycle, pre-approved) or place the two groups by explicit sites. Do not disable the coverage check.
4. First col kit past GPL: confirm `OT_HOLD_FF_MARGIN = 25` in `config.mk` and read the CTS hold class line before 200 more launch.

### Lever 2. Sited tail copies (QC st_a, KV PV)

**Evidence.** Headline 3 and 4 (V). Unsited result stands: -901.39 -> -912.09 (V, 21:20). Yosys folds unkept copies: 3,155 of 7,040 flops on pv_v12, 35 of 140 on st_a (R). Keep module `ot_dp_dly_keep` READY @6fc8c4a3 with `types.<t>.sites` anchor rows (R).

**Fix.**
1. TAIL-REPL: place `splitk` to CTS now with the bind `sites` rows loaded FIRM by the r650 anchor path. This is the only QC proof and it is not running. Acceptance: `rs_n_c_p` wire under 150 ps, CTS wns better than -250.
2. FABLE-FIX-KV-HG: on the pv_v12 proof read the `OT_TAIL_SITE` line first (`copies N of 7040 sited`, `over_380`, `core_crossing`, `in_halo`). Any `core_crossing` > 0 is the same defect as the 29 detour hops: the anchor must use the routed path around kv3_pv_pair (M1 to M7 OBS). Then reg-to-core against -1,197.
3. COORD/KV: PV types cross 400 k only because of the pad flops (pv_v3 467,307). Waive as in r682; a partition split of a PV column is not wanted. If GPL then stalls for size, cut K: tail copies only on pads with spread over 380 um.
4. The 1,822 short chains on pv_v12 and the pad < K buses need plan stages regardless (R, CHAIN 22:28); they belong in D22s/D23, not in the split.

### Lever 3. HEAD: three types

**Evidence.**
- hd_serdes (R, SD9F 23:20; V on the build state): one stage holds an 8-level XOR rank; sd9f -105.6, sd9g3 -184.09 TT and hold -44.59 on the same family. PPCYC removes one level only.
- lep_pair vE28 (V, epyc9 `lep_ve28/kit/.../run_finish.log`, `postcts_gate_TT.log`): at 6_report (RCX 124,229 nets, IR 1.32 %); GRT-stage gate `pinreg mean 555.05 bound 450.00 ... setup_est 11.75 hold_est -203.93 PASS`. No sign-off file yet.
- hd_lep0N p2 diagnostic (V): 3_3 GPL iteration 210, overflow 0.42, past the band stage.
- Die (V, epyc10 `fable-die-head/base/head/nf15f_t2/CHAIN.log`): combo GRT TT/FF 0 / 0 / 0 at 0.37 %; TT intra +572.03, seam +656.04; seam contract +9.08 (W 90, need 80.92); intra kit-contract -76.07 (W 22, need 98.07, 44,945 pairs). Hold measured on 0 of 585,476 pairs.
- M8 lock (V `m8/lock.log`, R for the totals): tree2 clock legs sit on granted type tracks, e.g. hd_turn_a 150, hd_turn_b 175; 4,321 in 14 types.

**Fix.**
1. FABLE-FIX-HEAD-SD9F: sd9h (PW16 + PW8) is the build of record. At GRT read `tt_setup_repair_grt.log`; expect 5 to 6 levels in the window stage. Stop PPCYC/SPCYC forms once sd9h shows TT >= -42 at GRT; they cost a cycle and fix less.
2. FABLE-FIX-HEAD-LEP0N: the vE28 core has 555 ps mean insertion against a 450 bound. Take the four pair tap offsets from its `clock_contract.json` when it signs, not from the 450 target. Its -204 hold estimate is port-side; close internal hold with r583 as on hei3.
3. HEAD-PLAN-R4: one pack = plan_grown2 + vE28 views with `bb.v` default KCRED 28 + related-pair `per_port_ps` for hd_lep0N and hd_mesh (file in `lanes/handoff/`). The routed window need of lep0N is 163 ps whole-set; the 63 ps figure was placement RC and must not size anything.
4. FABLE-DIE-HEAD: t2g (die clock with granted tracks as M8 obstructions). Types do not re-sign.

### Lever 4. Small routed hold misses: ECO the routed DB

**Evidence.**
- (R, SVC2 22:5x; V that mm6, mm7 are at CTS and mergex_mm6 at floorplan at 23:11) hslice mm4, HM 30, guards off: +2.83 before route, -3.27 routed, -6.15 at sign-off, TT +175.5, DRC 0. mergex mm3b -6.93, TT +97.83.
- Precedent (R): lep_pair hei3 closed 7 -> 2 -> 1 -> 0 pads with r583; sd9f ECO2 kept DRC 0 with 0 cells moved; QC L2 hold closes with the post-route ECO (6 signed).

**Root cause.** Pre-route margin does not predict the routed result on these cores (loss 6 to 9 ps on hslice, 20 to 40 ps on QC). Each margin step costs a full rebuild.

**Fix.**
1. FABLE-FIX-S81-SVC2 (P): run `hold_eco_internal_run.py` (r583) on the routed hslice_mm4 and mergex_mm3b DBs now. Both have large TT room, so a handful of pads closes them. Keep mm6/mm7 running as the second form; sign whichever passes first.
2. CAPSKEW-ECO: make that ECO the default last step of every kit that ends DRC 0, TT >= -42, internal hold between -50 and 0. This is the flow form of what three lanes do by hand.
3. Still open from 21:20: the chunk cap (2,000 buffers x 3) that stopped hslice at 11.7 k endpoints; `OT_HOLD_CHUNK_BUF_PCT=0` is under test in mm6.

### Lever 5. KV D22s and D23

**Evidence (V).** Headline 6. Rider gate (epyc7 `kv-pv-rider/gate2`): G0 PASS twice, LATCHECK `no *_bound_top.sv (the bind did not finish emitting)`; gate3 started 07:00Z. Wave: KV has 8 kit_rtl and 5 gen RUNNING, 0 at place or route.

**Fix (FABLE-FIX-KV-HG).**
1. Gate d22s on strict bind before anything else; the two try-2 errors were both invisible to G0.
2. Fold the rider (29 detour hops, 11 keepout stations) into the same plan if its bind passes this hour; else a separate event. No PV kit before keep + siting + rider.
3. D23 pc: 32 added taps, 68 total, max load 1,200 on measured sinks (R, KV-R3). Add the three forwarded pc clocks over 1,200 (3,347 / 1,303 / 1,271) to the same event. Drop tap_spill.

### Lever 6. S81 serdes

**Evidence (V).** epyc9 H17 `6_report.tmp.log`: RCX `411739 nets finished` at 22:18; unit 476135 still alive at 23:13 in final STA; no numbers yet. 204 `STA-1652 ... pin cland_fwd_fclk_out_ft{0,1,2}_o:N not found` SPEF warnings (98 / 60 / 33, plus 13 on `cland_up`).

**Fix (FABLE-FIX-S81-SERDES2).**
1. When STA ends: routed TT and internal FF hold by class; that read decides whether TAP-GROUP-CAP-1 (6,502 flops on clk_t42) returns.
2. Check the four forwarded-clock nets for missing parasitics before trusting their arrival (P: the SPEF refers to nodes the netlist no longer has after the pad strip).
3. t13 + 10 build on D8d with r678 once h-form PASS is posted.

### Lever 7. S81 die clock event

**Evidence (V).** Headline 2. `sta_droop.log` (legacy margins, not the gate form): TT intra +173.41 (0 negative), seam -0.46 (6 negative), skew 409 / 623; kit contract needs 341 intra / 548 seam against W 40; 0 measured hold pairs.

**Fix (S81-DIE-R3).**
1. Run the landed check with the tools and inputs of the r4j run: `fable-die-s81/reach_codex/run_current_r4_ca_phase.sh` end to end on the d7w_eco proof. Do not pass its arguments to the D7w tree tools, and do not drop `--start-partition-origins`; give the crossings their `src_part/dst_part`.
2. Name the 6 negative seam pairs in the legacy read and show them in the nominal form.
3. D8d (plan e291d6a8) proceeds to bind/G0; the route does not need more cut moves. Then one clock event: in-place K refresh + `clock.reserved_sites_um` after a census of the 42 signed DBs.

### Lever 8. S81 leaf and svc stops

**Evidence (V, wave stages).**
- PLACE-HPWL: t37 `7.8347e6 = 1.40 x 5.5789e6`; kv_leaf__t3 `1.0557e7 = 1.32 x` (new).
- svc: 11 rows (svc_hi pvso_entry t1 t2, rs t1, svc_lo rs_w t1 ...) FAIL kit_rtl `RuntimeError: closure failed for .../items/<item>/`.
- t56: `native module must declare exactly one memory array`. gunit__t1 KIT_PREFLIGHT 5 issues; serdes__t14 4 issues.
- (R, S81-FIX-OPUS 22:22) t22 died at GPL: `OT_CLAND no mapped cells under u_cland_collect_rst_rl_188`, because `build_rebase.sh` drops `--clock-landing` for non-col types.

**Fix.**
1. FABLE-FIX-S81-STRIP: t37 and kv_leaf t3 are one class (timing-driven repair grows area by 78 % on t37 and the placer re-spreads). Image the attempt_8 3_3 DB; if the growth is in the re-slotted ft bundles, cap the TD repair (r496 0.25/0.30) for the family. No ratio change.
2. S81-TYPES-R3: `--clock-landing` for every type with landing rows, then t22 (the GRT calibration over the M5 cores is still unmeasured).
3. FABLE-FIX-S81-SVC2: the svc kit_rtl closure failures are the old soft svc types; they end only with the shell rows (4 of 6 cores signed). Keep them held rather than relaunched.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| failure_breakdown 23:10 | intel2 | S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |
| wave stages, last 4 h | intel2 `autopilot/kit_wave_stages.tsv` | S81 place FAIL 81 (58 VPW got 0, 9 VPW distance, 4 relay_mid coverage, 2 FT off-grid, 2 HPWL); S81 route RUNNING 41, QC 8, HEAD 10; KV 0 at place/route; SPLIT-NEEDED kv3_pv_v3 467,307 and S81 kv_leaf__t2 462,435 |
| VPW marker | intel2 `lanes/handoff/tree_switch_s81.json` | key still present 23:10 |
| S81 die proto | epyc10 `s81-die-r3-proto/s81/d7w_eco/{CHAIN.log,grt_st_TT/combo_TT.log,ca/ca_plan.log,ca_r4_noparts/ca_plan.log,sta_droop.log}` | GRT 0 overflow; CA_PLAN rc 2 (unrecognized arguments), retry ValueError; legacy STA numbers above |
| svc reruns | epyc10 `fable-fix-s81-svc2/svc/build/{hslice_mm6,hslice_mm7,mergex_mm6}` | 4_1_cts, 4_1_cts, 2_1_floorplan; no exit files |
| hd_serdes | epyc10 `fable-fix-head-sd9h/{bench_b.log,sd9h_gen,sd9pa_gen}` | bench PASS; defines as stated; both in 3_1 GPL |
| HEAD die | epyc10 `fable-die-head/base/head/nf15f_t2/{CHAIN.log,m8/lock.log}` | numbers in lever 3 |
| lep_pair vE28, hd_lep0N p2 | epyc9 `head-lep0n-opus/lep_ve28/kit/...`, `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` | 6_report; GPL it 210 |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.tmp.log` | RCX done, STA running, 204 SPEF warnings |
| KV sited proof | epyc9 scratch3 `kv-hg-opus-site/proof/kv3_pv_v12/{face_flops.tcl,tail_copies.tsv,run_place.log}` | anchor sourced; 3_1 GPL; no OT_TAIL_SITE yet |
| QC keep proof | epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/splitk` | last log 1_synth; no place |
| KV D22 | epyc7 `kv-hg-opus/{d22gate,d22s/gate,d22s/gate_try1}/gate.out`, `kv-pv-rider/gate2/gate.out` | as headline 6 |

## 3. Stop list (the 21:20 list stands, plus these)

1. S81 col: no relaunch while `tree_switch_s81.json` carries the key. 58 fails in 4 h prove each one is wasted.
2. S81 die: do not read `STA_DROOP` (legacy margins) or `STA_LEGACY` as the landed verdict, and do not pass r4 CA arguments to the D7w tree tools.
3. S81 serdes: do not re-add TAP-GROUP-CAP-1 before the H17 routed timing. No new H17 route.
4. S81 svc: no further 30 ps margin rebuild of hslice (mm4 at HM 30, guards off, is -6.15 at sign-off). No relaunch of the soft svc types that fail kit_rtl closure.
5. S81 t37 / kv_leaf t3: no HPWL ratio change (branch 4eeee568 withdrawn; the real log is still 1.38 x). No t22 rebuild without `--clock-landing`.
6. HEAD: no CAPSKEW on sd9g3 (deficit 184 against about 130 per flop). Do not judge the die on `run_grt.sh` (signal-only runner over real views; the combo GRT is 0 / 0 / 0). Do not size lep0N windows from the 63 ps placement span.
7. QC: no partition split of st_a, st_b or hc (st_a is 54 k cells on the current event; 8 types waived by r682). No tt_ctlm region-only fix.
8. KV: no PV kit before keep + siting + rider. No pc judgement on tap_spill. No partition split of a PV column for the cell limit. Do not read the unsited pv_v12 run.
9. Tail split anywhere: no kit without the keep module; unkept copies fold back in synthesis.

## 4. Not checked

- H17 routed TT and hold (STA still running). The cause of the STA-1652 warnings (P).
- Any S81 route result of the 41 running rows; none finished in the window.
- hd_mesh route state and its numbers (R only). The t2g result. hd_lep0N CTS.
- sd9h past GPL; whether PW16/PW8 reach -42.
- KV d22s bind, rider gate3, the `OT_TAIL_SITE` line, the kv3_hg_v1 pilot.
- QC: N3 gate (blocked on a host disk, out of scope), the N3 clock-chain proof (queued), every N3 kit read.
- Whether r583 was already tried on hslice_mm4 or mergex_mm3b (lever 4 item 1 is P).
- The col_h9_r0_p3 place stop (`unclassified`, last GPL line only) and the gunit__t1 / serdes__t14 preflight issues.
- The relay_mid hop arithmetic in lever 1 item 3 is from the error text only; I did not open the plan rows.

---

# FABLE-CLOSURE-STRATEGY 2026-11-17 21:20 PST (2120): delta on 19:20

Reviewer: CLOSURE-STRATEGY-2120 (Opus, standing in for Fable, out of quota until 11-24). Read-only: no jobs launched, nothing killed or deleted. Technical PD only. HBM parked.
Gate (R-MINIMAL): DRC 0, routed TT >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.
Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal or estimate.

## 0. Headline

1. **Splitting the pad tails does not help unless the copies are also sited (V).** QC st_a proof `sle_st_a_v1__cl67389ecd` (epyc9 `/srv/opentallas-scratch/claude/tail-repl-qc-kit/{base,split}`, `4_cts_final.rpt`): wns -901.39 -> -912.09, tns -160,939 -> -159,509. The new copy `u_pd2_x_hc1_i_0_u_r0_5` drives one load, `u_u_r0/rs_n_c_p[0]`, but still has 1,585 ps of wire at 5,017 ps slew. The KV pv_v12 split kit (epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12`, still in GPL) has no anchor or relay-site knob for the `u_pd*_c*` copies in `config.mk`, and its GPL already added 153,615 buffers on 40,945 nets. It will show the same result. This is now the largest lever: about 27 QC and KV types depend on it.
2. **S81 has no die GRT result, although both proto arms "RAN exit 0" (V).** On epyc10, in `s81-die-r3-proto/s81/{d7w,d8c}`, the kit built, then all three GRT arms died in under 1 s at `mk_combo_kv.py: ModuleNotFoundError: No module named 'die_sta'`, because `OT_DIE_PLAN_TOOLS` is unset. TTA_TT and TTA_FF have no `arr_*.txt`, and CHAIN_DONE still ran. The s_4N_L1 congestion question is unanswered.
3. **HEAD hd_lep0N p2 is dead at global place since 20:19 PST, and no lane has posted it (V).** `fable-fix-head-lep0n/p2/hd_lep0N/run_cts.log` stops with `OT_CLAND no mapped cells found under u_core.u.g_plw.g_s\[0\][/.].*`. The cells do exist in `1_synth_odb.v` (`\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_`), so the CTS read HEAD-LEP0N-OPUS is waiting for will never come.
4. **H17 serdes reached DRC 0, fill and fillcell, then stopped at `6_report` (V):** `[ERROR ODB-0420] tmg_conn::detachTilePins: tilepin inside iterm` (final_report.tcl:13). The r644 in-pin segment ends inside the pin shape, and RCX/tmg_conn refuses it.
5. **Other technical place-stop classes in the last 12 h (V, `kit_wave_state.json`):**
   - S81 `OT_VPW_BANK distance exceeds 100um` on leaf t10, t45 and t74 (+1), up to attempt a9;
   - S81 `explicit FT site is not on a row/site` on t7 and t53;
   - `PLACE-HPWL` divergence on hd_tile (2.26x) and S81 leaf t37 (1.40x);
   - QC GPL-0305 on slw_st_b_v1__cle6023ec2;
   - `SPLIT-NEEDED` over 400 k cells on 7 QC types (hc0, hc2, st_b, 453 k to 487 k) and on kv3_hub_Wo (528 k).

## 1. Levers ranked by closure impact

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | QC, KV | Site the split tail copies at their consumer pins | QC st_a 11 types (44 hard rows); KV PV 16 types; PC bin-to-core | KV-HG-OPUS (r657 code), TAIL-REPL (st_a proof) |
| 2 | S81 | Get a real die GRT (fix the proto env), then D8d = re-sited stations + lattice snap + reset write-back + ist_rows | die route verdict; 8 G0 geometry ERRORs; col_h9_r1; t1/t15 serdes reset | S81-DIE-R3 |
| 3 | HEAD | hd_lep0N CLAND stage-row stop; lep_pair vE28 contract; related-pair windows | hd_lep0N, then hd_mesh and the last 3 HEAD types | HEAD-LEP0N-OPUS, HEAD-PLAN-R4 |
| 4 | all | Hold repair must reach the asked margin: no area-guard cut below the target, repair last, in the gate RC frame | S81 svc smc/hslice, S81 col family (236 items), QC N3 at 40 ps | CAPSKEW-ECO, S81-TYPES-R3 |
| 5 | S81 | Pad abut segment ends at the pin edge, not inside it (ODB-0420) | H17 sign-off, then 11 serdes types | S81-SERDES-GEN, S81-FIX-OPUS |
| 6 | S81 | Leaf place stops: VPW_BANK distance, FT site off row, CLAND band | about 8 to 10 leaf types | S81-TYPES-R3 |
| 7 | QC | N4 content: st_a flt_bank 2 stations, clk_t115 split, tt_ctlm pipe stage, coll_core offsets measured before apply, plus the >400 k splits | st_a, cbn_q00, tt_ctlm, coll family, 7 split types | QC-PLAN-R3, QC-N-OPUS, QC-TYPES-R3 |
| 8 | KV | D22 = 612 stations + facegrow + tap spill + tail split **with siting** | PV family, kv3_hroot/pv_v2/v2n band (5), pc pilot4 caps | KV-HG-OPUS, KV-R3 |

### Lever 1. Site the split tail copies (QC st_a, KV PV)

**Evidence (V).**
- In the st_a split kit, every `rs_n_c_p` end keeps its wire and slew: base 1,589 ps / 5,030 ps, split 1,585 ps / 5,017 ps.
- The bind and LEC are correct: 35 of 803 pads were split, giving 140 copies and +123 flops (R, TAIL-REPL 20:33).
- KV pv_v12: the split bind gives 7,044 copies and +19,382 flops (R). The kit has `PRE_DETAIL_PLACE_TCL = face_flops_release.tcl` only, with no anchor for the copies (V).

**Root cause.** r657 `land_pad_tail_split` changes the netlist only. GPL places each copy flop at the timing/wirelength optimum of its fan-in, which is the shared D-K trunk near the clock tap region (clk_t386 in st_a). The copy-to-pin hop stays at the full spread.

**Fix.**
1. KV-HG-OPUS: bind writes a sites record for every copy, at most 20 um from its consumer-core pin centroid (for QC st_a, the soft-leaf centroid from TAIL-REPL's 617dd4d9). The shared trunk stage goes at the pin-spread centroid.
2. The kit loads that record FIRM at 3_3, using the same anchor path as r650 `core_input_anchor.tcl`, so that both dies use one mechanism. A two-pass `type_relay_sites.py` regeneration is the slower fallback.
3. K from the r657 formula keeps each hop at or under `hop_um` 380.

**Acceptance.** On the st_a proof DB, `rs_n_c_p` wire under 150 ps and CTS wns better than -250. Then the same test on pv_v12 (before: reg-to-core -1,197).
4. TAIL-REPL runs the st_a proof as soon as the anchor exists. Do not wait for N4.

### Lever 2. S81 die GRT and D8d

**Evidence.**
- Lever-2 proto chain (V): `CHAIN.log` shows KIT 0, three GRT arms, each `mk.log` with `ModuleNotFoundError die_sta`, TTA 1 FileNotFoundError, CA_CHAIN 1, STA_DROOP 1, then `CHAIN_DONE`. `ot-run` reports exit 0. The same applies to d8c.
- D8c (R, FABLE-PD-S81-2100):
  - moved macros cover 2,296 ft station bits in 8 slots;
  - t1 `rst_rl_170` is gone and t15 `rst_rl_244` is 690 um away;
  - `ist_rows.py` and `cut_census.py` are not in the tree;
  - the 12 moved origins are off the 8.64 um lattice.

**Fix.**
1. S81-DIE-R3: in `proto_die.sh`, export `OT_DIE_PLAN_TOOLS=<tree>/tools/die_plan`. Make the chain exit non-zero when any GRT arm has no `arr_*.txt`. Rerun the D7w arm now; it is the applied plan and needs no D8.
2. Read three things from that run:
   - total overflow;
   - the gcell map over s_4N_L1 (y 19.77 to 21.0 mm), and over s_5S_L0, where the new worst cut segment (0.577) sits;
   - routed clock skew on related pairs.
3. D8d:
   - choose each core's dy so that it clears both the cut line and the station rows of that slot, as a multiple of 8.64 um;
   - otherwise re-site the 8 slots' stations with the generator;
   - build with r666 + gen4 (bind, then `local_reset_writeback.py`, then G0);
   - carry r652 `ist_rows` and r645 `cut_census`;
   - expect G0 with 0 geometry ERRORs, bind rc 0 and LATCHECK 873/873.
4. Run the D8d die GRT A/B against D7w before D8d applies. If the D7w die GRT shows s_4N_L1 below 100 % with no overflow, D8 is not needed for the route, and only the station and reset fixes matter.

### Lever 3. HEAD hd_lep0N

**Evidence (V).**
- p2 failed at 3_3 with the `OT_CLAND` error above. `landing_placement.tcl` lines 323 to 325 hold three `stage:plw_s0..s2` rows. The error is raised when `hit` stays 0 (line 2492).
- The cell names exist in the netlist, so either the escaped regex does not match the ODB names, or every flop was already in `cland_done` from an earlier entry (P: in that case the `continue` leaves `hit` at 0). Both are tool defects on a placement hint, not a plan fault.
- lep_pair vE28 (epyc9 `head-lep0n-opus/lep_ve28`) is in 5_1 GRT hold repair: `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03 at margin 10. Insertion is 586 ps against a 450 target (R).
- tree2 die GRT is at extra iteration 11/50 with a 75 % derate on M4 to M7, so it is congested. Result not yet available.
- tree2 placement-RC clock STA: 195 lep0N taps span 62.9 ps TT (R, 20:22); the kit SDC gives each port a 89 to 96 ps window.

**Fix.**
1. HEAD-LEP0N-OPUS: in `landing_placement.tcl`, count already-placed members as a hit, or test the regex on the 3_2 ODB with `get_cells`. Relaunch p2 from 3_2, not from synth.
2. Replace the stale rp21x per-port windows with related-pair windows from tree2 (`die_sta_related --kit-window-related`). That is the only cure for the cross-tap hold class; more margin is not.
3. HEAD-PLAN-R4: re-derive the four pair-clock tap offsets from the vE28 `clock_contract.json` (about 586 ps) when it signs.
4. When tree2 GRT ends, post the overflow and the gcells for x 880 to 1160 and 1230 to 1472.
5. hd_tile PLACE-HPWL (2.26x) is the same divergence class as S81 t37 and QC cle6023ec2 (lever 6, item 3).

### Lever 4. Hold repair that reaches its target

**Evidence.**
- (R, S81-FIX-OPUS 20:30) smc mm3b r2r FF -10.62 and hslice -5.92. The ORFS hold guard cut HM from 30 to 19 (a projected +8.9 util points over the 8-point limit), then MET-FIRST repaired at HM 0 and stopped.
- (V, 19:2x) The same order problem exists on QC: on slw_sc_v2 the GRT hold repair ends at +0.15, then TT setup repair runs after it.
- (R) Col item_env `OT_HOLD_FF_MARGIN_PS` 10 replaces the die key (25) and the family floor (`_fam = None if _hm`).

**Fix.**
1. CAPSKEW-ECO:
   - when the area guard trips, lower the margin no further than the gate target (0 plus the 20 to 40 ps routed loss already measured), and log it;
   - never fall back to HM 0;
   - run the final hold pass after the setup repair, in the gate RC frame.
2. The mm4 runs (guards off) are the A/B for this. If they sign, make guards-off the svc default.
3. S81-TYPES-R3: the 10 -> 25 change on all col item_env rows. Confirm `OT_HOLD_FF_MARGIN = 25` in the first col `config.mk`.

### Lever 5. Serdes: ODB-0420 at finish

**Evidence (V).** H17 `6_report.log:27` shows ODB-0420 after `5_3_fillcell` and `6_1_fill` passed. Route was DRC 0 at iteration 5, with 1,089 pad nets carrying the r644 segment (R).

**Root cause.** The hook draws a wire whose endpoint lies inside the macro iterm's pin shape. tmg_conn, which RCX and `estimate_parasitics` use, rejects a tile pin inside an iterm.

**Fix (S81-SERDES-GEN).**
- Preferred: end the segment exactly on the pin boundary (the pin-edge point on the access layer), so tmg_conn sees a normal connection.
- Alternative: the strip-before-RCX hook in test, but it must not leave these nets "unrouted" for RCX.
- Prove it on the H17 `6_1_fill.odb` copy; do not route again.
- Then run t13 from the D6z generator (running, epyc10 unit 306723) with the fix, and the TAP-CAP-CENSUS on the first CTS of each of the 11 types.

### Lever 6. S81 leaf place stops

**Evidence (V).** In `autopilot/kit_wave/s81_ot_s81sl_leaf__t10_*/a9` the error is `OT_VPW_BANK distance exceeds100um at u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0[0]`. The same error appears on t45 and t74 at attempts a4 to a9. Leaf t7 and t53 stop on an FT site off a row (`ft3,1,0 82.9376 176.8544`).

**Root cause (P).**
- OT_S81_VPW_BANK (r-strip, opt-in) clusters the VPW flops beside "both real SRAMs" and fails hard when the bank is over 100 um away. In lf4 sub-leaves the SRAM it chooses is not in the same sub-leaf.
- The FT site x is not snapped to the 0.054 um site grid (82.9376 is off-grid).

**Fix (S81-TYPES-R3).**
1. VPW_BANK chooses the SRAM of the same `u_u_lfN` instance. Under R-MINIMAL, a bank over 100 um gives a WARN and the flops are left to GPL.
2. The generator snaps the FT station xy to the row/site grid.
3. The PLACE-HPWL stops (t37 1.40x, hd_tile 2.26x, QC cle6023ec2 GPL-0305) get one retry of the converged DB without region guides and with the r496 td 0.25/0.30 GPL setting, not another unchanged relaunch.

### Lever 7. QC N4 content

**Evidence (R, QC-N-OPUS 19:5x).**
- st_a `flt_bank` r2 -> r0 runs about 1,000 um. The r1 -> r0 (482 um) and r2 -> r1 / r3 -> r2 (516 um) pairs are also over 405 um.
- clk_t115 has two clusters 200 um apart (W 330 to 359 ps, E 321 to 326 ps). clk_t50 is one hop latch: no split.
- tt_ctlm: 949 ps of data over 31 cells, about 700 ps of it logic. The period is 833 ps.
- The coll_core and cbn_q00__cldbcda913 clock-chain inputs are gone from every host (R, QC-PLAN-R3 19:48).

**Fix.**
1. QC-PLAN-R3, in N4:
   - 2 stations on r2 -> r0;
   - check the three other flt_bank pairs for live nets and add stations where they are live;
   - split clk_t115 at about (600, 2390) and (820, 2470);
   - add 1 pipeline stage in tt_ctlm `u_core`. A region alone removes at most about 250 ps of wire against a 760 ps budget for 700 ps of logic, so it cannot close.
2. QC-N-OPUS: regenerate the clock-chain inputs from the N3 plan before N4 applies. coll_core is `clock.source`, so all 43 new taps start unmeasured.
3. QC-TYPES-R3 with QC-PLAN-R3: the 7 types over 400 k cells need a partition split in N4. The +1,032 head-pad flops on hc in N3 make them larger, not smaller.
4. Carry the halo fix `claude/qc-pad-chain-halo-1117` into N3 by a tools refresh before the cb kits generate. Without it the third HB4 and the pipe register sit inside the r648 strip.

### Lever 8. KV D22

**State (R, KV-HG-OPUS 20:48 to 21:07).** D22 is composed on plan f9eeac833487 with:
- 189 PV stage rows and 612 stations (+99.5 k flops, +612 cycles on 187 lanes);
- `tap_spill_um 600` on 3 kv3_pc_v1 (this answers pc pilot4: 10 taps over the 1,200 cap, clk_t4 at 9,664);
- 6 raw-branch band rows;
- tail split `^kv3_pv`.

The tools refresh is applied (src `_t2509079`, with r641 and r657). Facegrow fix b917b3be is READY for the writer-face band class (kv3_hroot, pv_v2, pv_v2n, pv_v6: 5 rows). The build is moving to epyc7 because epyc10 scratch is full.

**Fix.**
1. Add lever 1 siting before the D22 kits generate. Without it, D22 PV kits repeat the st_a -912 result.
2. Merge b917b3be into the D22 tools.
3. On the first pc kit, run `tap_cap_census.py` on its CTS log and expect no tap over 1,200.
4. kv3_hub_Wo (528 k) needs a split row in D22, or it stays REFUSED.

## 2. Evidence I opened this round

| item | file | result |
|---|---|---|
| QC st_a tail split | epyc9 `tail-repl-qc-kit/{base,split}/run/reports/.../4_cts_final.rpt` | wns -901.39 / -912.09; tns -160,939 / -159,509; copy `u_pd2_x_hc1_i_0_u_r0_5` -> `u_u_r0/rs_n_c_p[0]`, slew 5,017.47, wire 1,585.02 |
| KV split kit | epyc7 `fable-fix-kv-hg-chain/tailsplit/kit_split/kv3_pv_v12/{config.mk,3_3_place_gp.tmp.log}` | no copy anchor; RSZ-0038 153,615 buffers in 40,945 nets; still in GPL (unit 229217 active) |
| S81 die GRT proto | epyc10 `s81-die-r3-proto/s81/d7w/{CHAIN.log,grt_*/mk.log,tta_TT.log}` | `ModuleNotFoundError die_sta` in all 3 arms; no `arr_TT.txt`; chain reported done; d8c the same |
| hd_lep0N p2 | epyc9 `fable-fix-head-lep0n/p2/hd_lep0N/{run_cts.log,landing_placement.tcl,1_synth_odb.v}` | GPL stop at 04:19 UTC (20:19 PST), OT_CLAND `g_plw.g_s[0]`; flop `\u_core.u.g_plw.g_s[0].u_st.q[0]$_DFF_PN0_` present |
| lep_pair vE28 | epyc9 `head-lep0n-opus/lep_ve28/.../5_1_grt.tmp.log` | `OT_HOLD_MM` SS setup -8.44 / FF hold -177.03, margin 10, repair in progress |
| tree2 die GRT | epyc9 `head-die-r/nf15e_e10/hr4/clock_rs8/tree2/kit/grt/grt.log` | derate 75 % on M4 to M7, extra iteration 11/50 at 05:10 UTC |
| H17 | epyc9 `fable-fix-s81-serdes2/H17/.../6_report.log` | ODB-0420 tilepin inside iterm, after fill |
| wave FAIL rows, last 12 h | intel2 `autopilot/kit_wave_state.json` | technical: VPW_BANK 4 (S81), FT off-row 2, PLACE-HPWL 2, MPL-0041 2 (kv_leaf t1/t3), GRTM edge_outline 3 (c1x_C t7/t9, slw_sc_v2), MPL-0034 2 (st_a), GPL-0305 1, SPLIT-NEEDED 8, KV CLAND band 5 |
| failure_breakdown 21:10 | intel2 | signed S81 42/394, HEAD 23/26, QC 24/130, KV 6/56 |

## 3. Stop list (the 19:20 list stands, plus these items)

1. Do not relaunch any tail-split kit (QC st_a, KV PV, D22) without copy siting. It is proven a no-op: -901 -> -912.
2. Do not read an `ot-run ... exit 0` from `proto_die.sh` as a die GRT result. Check that `arr_*.txt` exists.
3. Do not change region-guide box size or registers per region for GPL-0305. It was proven not to be the lever (QC-TYPES-R3 19:44).
4. tt_ctlm: a region-only fix cannot close 700 ps of logic. No clk_t50 split (one hop latch).
5. HEAD: no tree re-cut for lep0N (63 ps whole-set spread). No hd_lep0N relaunch from synth. No hold margin increase.
6. H17: no new route attempt. The defect is at finish (ODB-0420); test the fix on the routed/fill ODB copy.
7. S81: no D8d apply without a die GRT number on D7w. No hand edit of `rst_rl_N`. No VPW_BANK relaunch unchanged (t10 is at a9).
8. QC N3 cb kits: no generation before the halo fix is in the tree.
9. svc: do not raise the hold margin again while the area guard still cuts it. Fix the guard first (lever 4).

## 4. Not checked

- The S81 D8d build. I found no d8d directory on epyc8 or on the hub.
- smc/hslice mm4 results.
- The N3 bind result.
- The kv3_pv_v12 split kit past GPL.
- The tree2 GRT overflow numbers.
- Whether the hd_lep0N CLAND miss is the regex or `cland_done` (both are P).
- The VPW_BANK root cause beyond the error text (P).
- The 4 KIT_PREFLIGHT issues on dsdv_slice_c1x_C (14 rows; the class may be technical).
