# FABLE-TYPES-QC-WEST 2026-11-14: root causes for the unclosed QC slw_ types

Scope: the 49 unclosed `qwen_compute` types named `slw_*` (fe 5, fw 6, hc0-3 10, sc 5, st_a 5, st_b 5, stm 6, su_c 2, su_l0 3, su_l1 2). Read-and-diagnose: wave state, kit logs, gate logs, place dumps (`geom.tsv`) and SDCs of about 45 kit dirs on 6 hosts, plus two read-only STA probes on saved `5_1_grt.odb` (ot-run, intel1, 40 GB each). Nothing shared was changed, no job was touched.

Status words: MEASURED = read from a log, dump, SDC or probe; INFERENCE = fits the numbers, not proven.

Reviewed: 47 types with a physical problem on record. Skipped: su_l1 x2 (no failure on the current plan). su_l0 x3 is in FABLE-HARD-QCHEAD section 2 and is only referenced here.

## 0. Verdict in one table

| # | cause | types | status | owner |
|---|---|---|---|---|
| A | Reset-start wire: one raw-reset flop to `u_cland_rstart_tx`, 1,346-1,429 um in one cycle | sc x5, st_b x5, stm x6, fe, hc0-2 (every type with a relay tx) | MEASURED, generator fault | DIE-QC-103 |
| B | Cross-type lanes of 980-1,560 um in one cycle (ring to bin, bin to core to bout) | fw x6, su_c x2, st_b (x_fw_i 591 um), stm (INFERENCE) | MEASURED on fw_v2: 2,164 endpoints in 9 lanes | DIE-QC-103, TYPE-QCCOLLN |
| C | Tap window charged on cross-tap paths (65-135 ps), flops of one block on two taps | all; it is the whole violation on fe_v1, sc_v2, st_b_v1, hc0 | MEASURED | DIE-QC-103 |
| D | su_c: core `qfd_dv_s8x_vmr` clock pin has no access; core `prog` tap 288 ps early, FF hold -397 ps | su_c x2 | view MEASURED; hold mechanism INFERENCE | QC-CORES-HEAD |
| E | hc1: real overflow 20.8 k at 370-385 k cells | hc1 x3 | MEASURED count, no map read | DIE-QC-103 |
| F | st_a: children not signed (WAIT-CHILD) | st_a x5 | from TL-QCSTAV2 and FABLE-PLAN-EVENTS | TL-QCSTAV2 |
| G | Already answered elsewhere: DRT-0206 (strap pins off track), DRT-0255 (PG), su_l0 DRC 3, host-memory kills | fw, sc, stm_v3 / hc0, hc2, st_b_v1 / su_l0 / 17 runs | MEASURED, fixes in flight | TYPE-QCCOLLN, PG-AWARE-1, NEARMISS-ECO |

The main point: **no slw type has a logic-depth problem.** On every worst path 27 to 39 of the 31 to 60 cells are repeaters. The misses are distance and clock-window, and both are set by the plan and the generator, not by the route. Geometry already flagged them (`r2r` 953-1,777 um against 405, `relay_collapse` up to 4,069) but those rules are advisory, so the wave kept building forms that cannot meet -42 ps.

Measured wire speed, for sizing fixes: the fw_v2 `cmd_wi` hop covers 1,558 um in 1,144 ps of repeaters = 0.73 ps/um. One cycle carries about 800 um with no logic after clock-to-q, setup and a 78-ps window.

## 1. Latest result per family (today's kits, plans s29q102B0 / S / S2)

| family | cells | outline um | GRT TT setup est | end of the run |
|---|---|---|---|---|
| fe v1/v2 | 232-234 k | 622 x 1832 | -45 on 1 endpoint (cl95cd1d0c) | host memory (Error 241, rc 137) x5 |
| fw v1 | 279 k | 622 x 1832 | -236 to -276, 1,043-1,990 endpoints | Error 241, DRT-0206, one live at DRT |
| fw v2 | 263 k | 622 x 1832 | -439 / -446, 1,989-2,164 endpoints | DRT-0206 x3 |
| fw v3 | 263 k | 622 x 1832 | -259, 1,170 endpoints | Error 241 |
| hc0 | 360 k | 622 x 717 | -2.5 / -11 | DRT-0255; one killed (SIGTERM) after gate PASS |
| hc1 | 370-385 k | 613 x 717 | not reached | GRT-0116, overflow 20.8 k |
| hc2 | 351 k | 613 x 717 | +22 | DRT-0255 (116,216 violations at stop) |
| hc3 | 342 k | 622 x 717 | not reached | rc 137 (memory) |
| sc v1/v2/v3 | 302-320 k | 613 x 1832 | -65 to -185 | DRT-0206 x4 |
| st_b v1/v2 | 365-393 k | 622 x 1339 | -102, 263 endpoints | DRT-0255; one `grt183_make.sh` syntax error (in-place patch) |
| stm v1/v2/v3 | 283-287 k | 613 x 1832 | -258, 346 endpoints (v3) | DRT-0206, Error 241, rc 137 |
| su_c | 270 k + 9 macros | 1227 x 1400 | not reached | FF hold stop -397 on 5,349; DRT-0073 |

Older routed results on plan efdb36e864 (11-05 to 11-09) show the same picture after detail route: stm -670 to -913 ps on 2,822-3,594 endpoints, st_b_v1 -408, hc2 -229, hc1 -194, fw_v3 -147, fe_v2 -110.

## 2. Cause A: the reset-start wire

MEASURED
- sc_v3 (`s29q102B0` attempt_3, intel1), STA probe on `5_1_grt.odb`: 157 violating endpoints. One is real: `u_cland_rst_cws2_i/q -> u_cland_rstart_tx` at -162.19 ps. The other 156 are input port to feed-through flop at -22 to -24 ps (inside the -42 gate).
- The path is 27 repeaters, one inverter and one AND2: 1,158 ps of data.
- Both ends are sited by the generator (`landing_placement.tcl`): the raw copy at (24.8, 1763.1), the tx flop at (607.0, 915.8). Manhattan distance 1,429 um.
- Same pair elsewhere: st_b_v1 1,346 um (`u_cland_rst_b_hw_ctl_hc3_i`), fw_v2 1,361 um (`u_cland_rst_cmd_wi`, -275.6 ps), sc_v1 cl5e017c6f -185.26 ps. It is the `r2r_worst` pair of 13 kit dumps (sc, st_b, stm_v1, stm_v3, fe_v1, hc0, hc1; hc2 has `u_cland_origin/pd -> rstart_tx`). TL-QCSTBV1 saw it at -226 ps after CTS on sle_st_b_v1.
- Why: `tools/die_plan/clock_landings.py`, `_origin_rtl`, `local_raw()` takes `next(iter(ca_raw.values()))`: the first raw-reset copy in dictionary order, wherever it sits. The tx flop sits at the `cland_rstart_out` pin.

Dead end: any reroute, density or ECO form. One wire of 1.4 mm cannot make 833 ps with a 78-135 ps window.

Fix (generator, no plan change)
1. `local_raw()` returns the raw-reset copy whose site is nearest to the consumer (the tx flop, the origin). `landing_place.py` already has every site.
2. If the nearest copy is more than 600 um away, emit one `ot_dp_rrelay` at the midpoint. It is a reset level, so one more cycle of assertion or release has no lane effect; `clock_landing_verify.py` needs the extra stage in its expected tree.
3. Add the pair to the kit preflight: site distance of every generator-placed flop pair over 800 um is an error.

Proof in one build: sc_v3 or sc_v2 regenerated from the current source. Expected: sc_v3 worst internal path gone, setup inside -42.

## 3. Cause B: cross-type lanes longer than one cycle

MEASURED, fw_v2 (`slw_fw_v2__cl8f84514c` attempt_5, intel1; probe reproduces the gate WNS -446.12 exactly). 2,164 violating endpoints, by lane:

| endpoints | WNS ps | from -> to | geometry |
|---|---|---|---|
| 551 | -243 | `u_bin_x_fe_p1_i` -> `u_core.ch_dn_o` | E face (608, 740) to core flops spread x 268-616, y 204-937 |
| 543 | -295 | `u_bin_x_stm_p1_i` -> `u_bout_st_wo` | E face (607, 1479) to W face (13, 829): 1,244 um |
| 536 | -118 | `u_bin_x_stm_i` -> `u_bout_st_wo` | E face (607, 1218) to W face (13, 829): 983 um |
| 207 | -363 | `u_bin_x_ctl_i` -> `u_core.ch_dn_o` | bins stretched y 693-1781 from the N-face ring |
| 116 | -446 | ring `cmd_wi` -> `u_bin_cmd_wi` | ring at the W pins (28, 160), bins at (507, 1238): 1,558 um |
| 57 | -428 | ring `dr_wi` -> `u_bin_dr_wi` | ring (28, 363), bins spread y 393-1415 |
| 56 | -184 | `u_core.ch_dn_o` -> `u_bout_ard_wo` | to W face (13, 69) |
| 34 | -136 | ring `x_ctl_i` -> `u_bin_x_ctl_i` | |
| 23 | -44 | `u_bin_x_sc_i` -> `u_bout_sc_wo` | |

- The fw core has 3,930 flops and spans 350 x 1,140 um: it is pulled apart by buses whose pin windows on the east and west faces are 390-650 um apart in y.
- The bin register behind a landing ring has no site. The ring is fixed at the pins; the bin follows its consumers. fw_v1: `x_ctl_i` ring to bin 1,289 um, `cmd_wi` 654. fw_v3: `treq_wi` 725, `dr_wi` 636. su_c: `x_ctl_p2_i` 1,038 um (551 bits), `x_ctl_p1_i` 995 (552 bits). st_b_v1: `x_fw_i` 591.
- fw_v1 and fw_v3 worst path: `u_bin_x_fe_p1_i/q[551]` to `u_core.ch_dn_o[*]`, 37 cells of which 30 are repeaters, 1,273 ps.
- Stations exist only for feed-through slots (`relay_bay_table.tsv`: cws0, rsn, rsf, x_st_a_fe at 247-286 um per hop, all PASS). No lane that ends in the core has one.
- `GPL_TIMING_DRIVEN = 0` in these kits; at 3 % fill the placer has no reason to keep a lane short.

INFERENCE: stm is the same class. stm_v3 worst path `u_core.u_stream.wd_q[100] -> lane_c[438]` is 33 repeaters and 5 gates (1,203 ps), 346 endpoints. I did not read the stm place dump (not on disk for that attempt).

Dead ends
- Every route-stage form of fw and stm (density, hook, seed, late ECO): -236 to -446 ps on 1,000-2,164 endpoints is not an ECO.
- The fw strap-snap and PG forms of TYPE-QCCOLLN: needed for DRC, they do not touch timing. The live fw_v1 clc7ddab13 DRT (epyc2) will end routed at about -236 ps.

Fix (plan event, cycles are spent)
1. fw: one internal station per lane on the five core lanes (x_stm_i, x_stm_p1_i -> st_wo; x_fe_p1_i, x_ctl_i -> ch_dn; ch_dn -> ard_wo) at the type mid-line x about 310. Each hop is then 600-650 um. Plan `internal_stations` and `kit_istations.py` already place such flops; the bind adds one lane cycle per station, LATCHECK follows.
   Cheaper alternative for the two stm lanes only: move the E-face pin windows of `x_stm_i` / `x_stm_p1_i` (y 1171-1526) to the y range of `st_wo` (735-923). That removes 390-650 um but moves the abutting stm pins too.
2. Ring to bin, all types: site the bin at its ring (same rule as pin registers), and carry the distance with the lane's pad chain. Where a pad chain exists it is free: fe has `u_pd13_x_fw_p1_i` (13 stages) placed in a heap, span 496 um with one hop of 395; `kit_istations.py` should spread pad stages evenly from ring to consumer. Where none exists (fw `cmd_wi`, `dr_wi`, `x_ctl_i`, `treq_wi`; su_c `x_ctl_p1_i`, `x_ctl_p2_i`) the plan adds one or two stations.
3. Make the reach rule blocking at G0 for these lanes with the measured number, not 405: a bin-to-capture or ring-to-bin distance over 800 um with no station is a plan error. (405 flags 6,000-9,600 captures per kit, most of which meet timing; fe_v1 has 6,202 and closes to -45 ps on 1 endpoint.)

Proof in one build: fw_v2 with the stations bound; the nine lanes above leave the violator list. Before the build: `auto_geom` on the placed database, largest ring-to-bin and bin-to-bout distance under 800 um.

## 4. Cause C: the tap window on cross-tap paths

MEASURED
- Each kit SDC gives every clock tap an early source latency from the die clock proof ("tap window MEASURED per port"). Sizes: st_b_v1 0-88 ps (53 taps, median 44), fe_v1 0-93, fw_v2 0-78, fw_v3 0-65, hc0 12-60, sc_v3 6-90, sc_v2 13-135 (55 taps, median 72).
- A path between two taps pays the capture tap's whole window; a path inside one tap pays nothing (CPPR).
- st_b_v1 worst path (-101.64 ps, 263 endpoints): two flops of the same adder, `u_u_r7.g_l8[0].u_add.g_exact.u_d.u_319 -> u_153`. Launch tap `clk_t113` arrives 247.55; capture tap `clk_t105` has early -78 and arrives 222.5 + window. Window 78 + tree skew 24.5 = 102.5 ps: the whole violation. The same path carries three hold pads (HB4, 225 ps), put there because hold charges the window in the other direction.
- sc_v2 worst path (-65.26 ps, 2 endpoints): `u_cland_x_su_l1_i/arm_cnt[2] -> u_cland_x_su_l1_i/u_fault_port`, one landing block on taps `clk_t17` and `clk_t5`; the capture window is 131 ps.
- fe_v1 (-45.24, 1 endpoint): capture 100 ps ahead of launch. hc0 cl4f54b7a3 (-10.98, 11 endpoints): 36 ps.

So four families miss the gate by the window alone, with timing otherwise met.

Fix
1. Tap assignment by block: flops of one leaf module instance (an adder, one landing ring with its counters and fault port) get one tap. This is the sink-to-tap map in the kit clock generator (`clock_taps.tcl` / the plan tap regions); a region boundary must not cut an instance. No plan geometry change.
2. Die clock: the largest windows (sc 135, fe 93, sc_v3 90, st_b 88) are die-tree skew between taps of one type. Tightening them is die clock work for DIE-QC-103; each 10 ps is 10 ps of setup and 10 ps less hold padding on every cross-tap path.
3. Until then these four are late-ECO candidates once routed: fe_v1 cl95cd1d0c, sc_v2, sc_v3 (after cause A), hc0 x2, hc2. Sizes 1 to 11 endpoints.

Proof in one build: st_b_v1 with the adder instances kept on one tap: the 263 endpoints leave the list and the HB4 count on `u_u_r7` paths drops.

## 5. Cause D: su_c

MEASURED
- `slw_su_c__cl92142dac` attempt_3 (epyc10) stops in pin access: `DRT-0073 No access point for u_bound.u_u_suvm_u_vm8q_u_va/ck (qfd_dv_s8x_vmr)`.
- The view: macro 250.56 x 216. Pin `ck` is one M5 rectangle 0.024 x 0.384 at (125.28, 107.808), the middle of the macro. The LEF obstruction covers M1 to M6 over the whole body (0 0 246.24 211.811), M5 and M6 included, with no window at the pin. Three instances (`u_va`, `u_vb`, `u_vc`) use this master.
- `slw_su_c__cl19bb38ef` attempt_4 (epyc7) stops earlier: `OT_HOLD_GATE FAIL FF wns -397.17, 5,349 endpoints, beyond the structural stop -294`.
- Its SDC has one outlier tap: `clk_c4` early latency -287.71 ps, against -17 to -62 on the other core taps. `clk_c4` feeds `u_u_suvm_u_vm8q_u_pg` (`qfd_dv_s8x_prog`), whose model clock depth is 472.71 ps against 254-287 for the other eight cores.

INFERENCE: the hold failure comes from that tap. It is the hd_host_e `u_epc` pattern of FABLE-HARD-QCHEAD section 3 (tap aligned to the deepest internal register, inputs captured much earlier). Against it: 5,349 is close to the 5,410 forwarded ring inputs the gate counts. I did not dump the failing endpoints; one FF hold report grouped by endpoint on `4_cts.odb` decides it.

Dead end: relaunching either su_c form. Both stop deterministically, and cl19bb38ef will meet DRT-0073 after its hold gate.

Fix
1. vmr view: open the M5/M6 obstruction around `ck` and bring the pin up to M6 or M7, if the core's own M6 is free there (check the signed database); otherwise re-export with the clock pin on a face. View-only when the metal is free.
2. prog core: bring its clock depth to the 250-290 band (rebuild the core's tree; re-sign is allowed) or set its tap from the pin-referenced arcs. Then the -287.71 tap disappears.
3. Cause B item 2 for `x_ctl_p1_i` / `x_ctl_p2_i`.

Proof in one build: su_c cl92142dac with the new vmr view passes pin access; the hold gate of cl19bb38ef passes with the prog tap inside the band.

## 6. Cause E, F, G in short

- **E, hc1** (`cl68f9248e__cle683a076` attempt_5, epyc10): GRT-0116. Overflow by layer M2 874, M3 6,348, M4 1,103, M5 5,980, M6 930, M7 5,242, M8 368: 20.8 k, 85 % on the vertical layers. 370-385 k cells in 613 x 717; hc0 with 360 k routes with 0. The hc1 kits carry soft rings `b_hw_i` (1,573 bits), `rs_n0`, `rs_n1` (514 each): about 67 k cells at 26 per bit (count from the FABLE-WAVE-REVIEW ratio, INFERENCE). First step: confirm the S3R kit binds them as hard cores; if it does not, that is the fix. I did not read a congestion map.
- **F, st_a**: no build since 11-12. Old plan: GRT setup -264 / -273, hold stall -92 on 15,692. Waits on the three new `sta_region_nb0` masters (S3R3). When it builds, causes A and C apply to it.
- **G, closed or owned**
  - DRT-0206: old kits put the ID strap pins half a track off (M5 x 311.040). Kits generated from the current source have them on track (311.064; checked on S3M2 sc_v2 and stm_v3). No further action; do not resume old kits from a pre-floorplan database.
  - DRT-0255 on hc0, hc2, st_b_v1: PG-AWARE-1. hc0 and hc2 meet timing at GRT (-11 to +22), so they are the best proof builds for it.
  - Host memory: 17 of today's about 45 slw runs that reached CTS or later ended with Error 241, rc 137 or SIGTERM. hc0 cl4f54b7a3 was killed after both gates passed.
  - st_b_v2 pva66d0f22: `grt183_make.sh: line 244: syntax error`, the in-place patch class.
  - Hold `port_in` -100 to -130 ps on about 2,000 endpoints in sc and stm: input ports with the IO shift, advisory, not internal FF hold.

## 7. What to stop and what to start

Stop
- Rebuilding fw (6 types) and stm (6) on the current plan: they route to -236 to -446 and about -258 or worse.
- Any su_c relaunch before the vmr view and the prog tap.

Start, in this order
1. Generator fix A (hours): unblocks sc x5 outright and removes the worst pair in 13 kits.
2. Tap assignment by block, C1 (hours to a day): turns fe, sc_v2, st_b_v1, hc0 from misses into passes or one-pass ECOs.
3. Plan event B for fw, stm and su_c lanes (stations, bin sites): the only way those 14 types close.
4. Core views D for su_c.

## 8. Evidence

- Probes: intel1 `/srv/opentallas-scratch2/claude/fable-types-qc-west/{fw_v2,sc_v3}/setup_summary.txt` and `probe.log`; scripts `sta_probe.tcl`, `run_probe.sh` beside them. Client logs intel2 `~/fable-types-qc-west/`.
- Kits: `/srv/opentallas-scratch/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/<event>/items/<type>/attempt_N/` with `gen/<type>/postcts_gate_TT.log`, `constraint.sdc`, `landing_placement.tcl`, `geom/geom.tsv`, `geom/auto_geom.json`.
- Not done: stm place dump; su_c hold endpoint dump; hc1 congestion map; the fw_v1 and stm_v3 probes (not admitted for memory, then lost to a client kill).
