# FABLE-FIX-S81-SLICEC-0045 handoff: S81 slice C family (c1x_C t1..t10, iq_C t1)

Lane: FABLE-FIX-S81-SLICEC (posts: lanes/posts/FABLE-FIX-S81-SLICEC.md). Started 2026-11-20 00:03 PST.
Lane dirs: epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-slicec` (clone `src`, scripts, proof `p1`), epyc7 same path (STA dumps, slim copy of the t9 kit).
State: root cause measured; one tool fix on main; J4 row corrections posted; private proof kit p1 for c1x_C t9 generated and launched (see "Proof p1"). Nothing is signed. No family build was started.

## 1. Root cause of TT -1,422 (measured, c1x_C t9 attempt_16 CTS DB, 10,160 failing endpoints)

Evidence: epyc7 `fable-fix-s81-slicec/eps2_t9cts.json` (report_checks, every failing endpoint), `eps2_t9cts.paths.tsv` (one line per path: slack, start, end, launch / capture clock arrival, cell / wire delay, levels, buffers, flight, xy), `eps2_t9cts.xy` (all placed instances). Scripts: `eps2.tcl` + `eps2.sh` (dump), `ana.py` (classes), `census.py` (flops per module with spread), `q.py` (xr faces), `c2c.py` (direct core-to-core nets of a bound module).

It is not one path, not logic depth and not cell count. Four structural classes, the same in every C type (CTS TT: t1 -2,568, t4 -1,412, t5 -1,500, t6 -1,572, t7 -1,506, t9 -1,422, t10 -1,526):

| Class | Ends | Worst | What it is |
|---|---|---|---|
| A direct core wires xr <-> eg | 131 | -1,422 | xr.x_scale -> egg.scale 923 um, x_eps -> egn 725 / 880 um, egg.g / g_c / g_v -> xr.eg_* 800-824 um. No cell on the wire, launched from a negedge output flop (xr OLAT=1, eg negedge out), so the budget is T/2. Wire delay alone 1,000-1,280 ps. |
| B kit clock taps | ~5,800 | -972 | 53 taps for 95,939 flops (clk_t31 15,011 sinks, t30 8,068). Tap means 217..733 ps, cores balanced to 250, plus the -105 early window on every cross-port path. Soft flop -> core pin paths lose 200-480 ps: xf.u_x.dl_d -> finish core f_d (1,603 ends), xg gd_b -> SRAM wd_in (2,113), relay -> xr lo_d / e_d / p_d (830). |
| C xr half-cycle faces against far stations | ~1,500 | -711 | xr outputs leave the pin about 770 ps into the cycle (W face x 398: sw_d, c_d, g_d; S face y 43: rb_d, x_s, x_eps, x_scale). The first leafdn station is 550-1,026 um away: the TYPE-SAFE-2 stations were sited from the cap pins, and the same buses also launch from xr. xr inputs (FACE_LAND=2 negedge pin flop): the d1 relay sits 150-440 um from the pin, at the midpoint, not at the sink. |
| D reach inside xf | ~500 | -1,110 | u_x.dl_d / id (one copy, the ring landing registers) -> f_d of five finish cores in a 950-um row, hops to 817 um in one cycle. u_x control iv -> wo_d / eo_d through 18-20 buffers in series (840-990 ps of cells for 3-7 real levels): u_x is about 1k flops torn over 900 um between xr, eg and the finish row. |

Cell count: 496,913 placed = 95,939 flops + 108,252 buffers + 124,467 anonymous logic + named cells. The landing / station / cland infrastructure is about 230k of it (u_ist_leafdn 42k, cland_leafup 34k, cland_xring 32k, ft 16k + 15k, bin / bout 47k). The c1x.C logic itself is small (xg.u_s 24k, xg.u_r 15k, xf.u_x about 1k flops). Splitting the type would not remove a failing class.

## 2. Done

1. main 1889edd4e1e `tools/die_plan/relay_depth.py`: valid / data bundles of the slice-C hub cores carry ONE depth (ALIGN_GROUP now holds several groups per source module: egg g / g_c / g_v; xrt cfg_, is_, c_, sw_, lo_, rb_, g_, x_s*). egn.o_* -> egg.n_* never gets a row (egg delays dd by the fixed norm latency; over the reach it is listed unfixed = core placement). Test `test_slice_c_bundles_stay_aligned_and_norm_gate_gets_no_row`; relay_depth suites 29 green.
2. FUNCTIONAL finding in plan_j3b 5bed28a94d9d, posted to S81-DIE-R3 (ROWS post 00:3x): c1x_C t9 and t10 carry xr.eg_v D1 / eg_c D1 / eg_d D2; iq_C t1 carries cap.cfg_d D1 / cfg_v D2. Bound as is, data lands one cycle after its valid. Correction: eg_v, eg_c -> D2 on t9 and t10; cfg_d -> D2 on iq_C t1. The other C types are aligned.
3. Tap table for c1x_C t9: `tap_resolve --span-um 300 --target 1000` on the placed registers: 53 -> 171 taps, max load 995, 0 taps over W+H 300 (max 295), predicted spread 13.7 ps. File epyc9 `fable-fix-s81-slicec/p1/t9_taps.json`.

## 3. Fix plan (rows for J4; R1-R3 are in proof p1)

- R1 clock: span-300 tap rows per C type (append to clock.taps, set clock.tap_span_um 300). t9 is solved. Register dumps of t1, t4, t5, t6, t7, t8, t10, iq_C from their live kit DBs: epyc9 `fable-fix-s81-slicec/regs/` (driver `dump2.sh`, log `dump2.log`); solve each with `p1_taps.sh` as the pattern (assert the hard-core origins equal plan_j3b first, as `mkplan.py` does). t3 has no placed DB yet.
- R2 relay_depth: the three corrections above; every later relay_depth run must use main >= 1889edd4e1e.
- R3 xr faces, 0 cycles where the count allows: first leafdn station inside the half-cycle reach of the xr W face. t9 sites in `mkplan.py` (leafdn_o0 (400,300) (400,610) (400,920); o1 (400,322) (400,632) (400,942) (440,1200); o2 (385,20) (385,375) (385,730) (385,1085) (600,1226.88)): same stage counts, every hop <= 356 um, cap pin -> first station <= 363 um. NOT covered: xr S-face rb_d / rb_v to leafdn_o0 / o1 (about 390 um round the core at T/2): needs one pin station (+1 cycle on rb) or rb on o2 only; and the d1 relays in front of xr lo_d / e_d / p_d need relay_sites at the xr SW corner (about (385,110)), not the midpoint.
- R4 xf locality (not in p1): either (a) re-floor the five finish cores from the 950-um row into a 3 + 2 block round u_x (farthest f_d pin centroid about 315 um from the id registers), or (b) an RTL delivery stage per finish core in ot_s81dv_xfin (f_v, f_t, f_base, f_d and go delayed together, result +1 cycle, declared). (a) costs no cycle and needs a whole-type visual pass; (b) needs the xfin bench and the latency rows.
- Rule gap for CBC / PRECHECK: the 405-um hop rule assumes a full cycle. A hop that starts at a negedge output face (xr OLAT, eg) or ends at a negedge pin flop (xr FACE_LAND=2) has about 310 ps, i.e. about 200-250 um. Station and relay siting must measure from EVERY source core of a bus, and site the last relay at a half-cycle sink, not at the midpoint.

## 4. Proof p1 (c1x_C t9, private kit, to GRT TT)

Form: D8h bound module (tree `kw45/src_s81_pin_3c913dbdfb23_d8h_1117_work`, tools overlay `rt_tools_launch/...d8h_1117_work@5802101050d7` = KIT-RD-1) + R1 + R2 rows + R3 leafdn sites. Scripts on epyc9 `fable-fix-s81-slicec`: `mkplan.py`, `p1_taps.sh`, `p1_kit.sh` (kit-rtl + gen phys), `p1_launch.sh HOST`, `p1_run.sh`. Private plan `p1/s81/plan_h2_2249.json`; kit `p1/dsdv_slice_c1x_C__t9/gen/dsdv_slice_c1x_C__t9`.
Status 2026-11-20 00:50 PST: kit-rtl PASS (relay_depth rows staged, receipt `p1/dsdv_slice_c1x_C__t9/rtl/kit_relay_depth.json`); gen phys running (`p1_kit.log`); not yet launched. Launch: `bash p1_launch.sh <host>` on epyc9 (copies the kit, starts `ot-run --mem 72 ... p1_run.sh ... grt`).
Read at CTS: `OT_TAP_BALANCE` (spread, was 273), `OT_TAP_CHECK` trees over 270 (was 36), `OT_CTS_POST_TIMING` (was -1,422 / tns -2.23M), then run `eps2.sh` + `ana.py` on the new 4_cts.odb and compare class by class with section 1. Expected residue: class D whole, rb_d S face, d1 relays at xr.

## 5. Next steps for the successor

1. Read p1 at CTS and GRT TT; post the class table against section 1.
2. Solve R1 for the other C types from `regs/`; hand S81-DIE-R3 one rows file (taps + relay_depth corrections + leafdn sites per type; the sites must be drawn per type, the cores sit differently in each).
3. Decide R4 (a) or (b) on the p1 residue; build p2 with it in parallel.
4. Only then the family build to sign-off and the export to rtx-pro ~/signed-export-1114 and AGIdock /archive. No wave relaunch of C types on the unchanged plan: all seven measured attempts fail the same four classes.
