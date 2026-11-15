# FABLE-REVIEW-CORES (Fable review + plan, last 2 unsigned S81 hard cores), started 2026-11-14 04:40 PST
Gates = R-MINIMAL (DRT DRC 0, routed TT setup >= -42 ps, internal FF hold >= 0). Sign-off bookkeeping stays with TYPE-GUNIT-L1F2 (AUTO-RESIGN rows on pass).
Lane dir (all hosts, same path): /srv/opentallas-scratch2/claude/fable-review-cores. Logs: intel2 ~/fable-review-logs/. Tools: epyc10 .../fable-review-cores/tools (mkform.py, bk_probe.py).

## 1 dsdv_gunit_l1f_bf (432 x 172.8, 105,748 cells, 0 macros, 2,689 pins)
Measured on the dead F2 run (epyc8 s81-cores-2/gunit_f2, 5_1_grt.log, 3_3_place_gp.log; renders viewed):
- Wire-limited block, not cell-limited: 21% utilization, yet GRT usage is 55.6% of all tracks (3.54 m of wire, 28.7 um per net).
  Horizontal layers M2/M4/M6 run at 71/61/53% (63% together), vertical M3/M5 at 57/32% (47%). The congestion map is saturated
  over the whole middle of the block with a full-height hot stripe at x 291. Final overflow was only 115 (max 2 per gcell).
- Cause 1 (self-inflicted, largest): the 16 READ bank guides (40.5 x 37.8 each) + META (43.2 x 43.2) are exclusive placement
  regions at 4.6-5.2% fill (0.6% META). They remove 26.4k um2 of the 68.6k um2 core (38%) from every other cell
  (GPL "Available Free Area 42251"). F2 freed the sc storage and g_e cachewrite from the banks but kept the F1 box size.
  The remaining 97% of the cells place at min feasible density 0.29 after +97% routability inflation in 62% of the core.
- Cause 2: the dominant wiring is horizontal (W write data -> E outputs, lane fold/sort exchanges across lanes), and the block is
  2.5:1 wide, so the horizontal tracks through a 172.8 um tall cut are the scarce resource.
- Bank positions ignore the pin lanes: svreg_data bank l drives s_val -> sv_lo lane l (l<8, S face) or sv_hi lane l-8 (N face);
  lanes sit at x 45.9 + 48.6*l. The F2 4x4 grid puts bank 4-7 up to 200 um from its lane.
- Running forms: a (504 x 201.6, M6, 0.4) should pass GRT (peak about 91%) but keeps the big boxes; b (432 x 172.8, M7, 0.3)
  adds only a vertical layer (M7) where horizontal is short, and 0.3 is at the F2 min feasible density 0.29: likely fails
  GRT again. Neither killed.
- DEFECT in form a (for TYPE-GUNIT-L1F2): its pins.json has only 4 of the 1,249 N/E pins moved to the new edges (ctl_hi[0],
  ctl_hi[10], g_a[0], g_a[10]); io.tcl has all of them. pin_audit.py compares the routed ODB with pins.json, so form a ends
  FAIL_POSTROUTE pin_audit unless pins.json is rewritten from io.tcl before the route ends (read only at audit time).
Forms launched 05:0x PST (all: same RTL/netlist/SDC/clock as F2, M6 ceiling, density 0.4, fresh synth, OT_LEC_ASYNC=0,
OT_HOLD_STRUCTURAL_ADVISORY=1 NONPORT_HOLD=1, goal finish; guides right-sized to 27.0 x 13.5 = 0.19 fill, META 10.8 x 10.8):
- g1 (rank 1 if it routes: no outline or parent change) 432 x 172.8, lane-aligned banks 8 x 2 (S row y 16.2, N row y 143.1).
  intel1 gunit_g1/dsdv_gunit_l1f_bf_gf5g1, unit oth-ubuntu-2239863-1794660887, log gunit_g1.otrun.log.
- g2 (rank 1 for margin) 432 x 216.0 (+43.2 height = +25% horizontal tracks, pin x unchanged), lane-aligned banks.
  epyc2 gunit_g2/dsdv_gunit_l1f_bf_gf5g2, unit oth-ubuntu-1237662-1794660886, log gunit_g2.otrun.log.
- g3 (hedge on bank position) 432 x 216.0, F2 4x4 bank centres (row pitch 54.81), right-sized boxes.
  epyc7 gunit_g3/dsdv_gunit_l1f_bf_gf5g3, unit oth-ubuntu-2200342-1794660891, log gunit_g3.otrun.log.
Pin rule of g2/g3: S pins unchanged; N pins same x, y = 215.958; W/E pins same x, y + 21.6 (450 M4 tracks). pins.json, io.tcl,
config.mk and freeze.json agree in each kit (mkform.py). The parent moves ba1 up by 43.2 per bf and shifts the W/E nets.
If none passes: next is 432 x 259.2 with the same guides (horizontal usage about 42%); only then M7.
Abstract: whichever form signs off, the parent gunit__t1 must take the corrected abstract (real M5 pin stubs, OBS cut over the
stub and the M6 window above it; constructor results/gunit_core_1/pin_access_1113 on claude/die-s81-89-gunit-1113@bbb2b73c09),
not the ORFS generate_abstract LEF (84 nm slivers under blanket M1-M6 OBS = DRT-0073). TYPE-GUNIT-L1F2 form c owns that.

## 2 dsdv_bksel_q (648 x 648, 61,941 cells, 33 macros incl. hard child pk2 194.4 x 194.4, 1,803 pins)
History: vS stalled in DRT (17.5k violations in the P W/E pin strips) -> vC cut escape strips; vC5 died GRT-0232 in the setup
repair's incremental route (channel east of P); C9geom died GRT-0183 on net45752 twice (epyc4 try1, epyc10 attempt 1) inside
the GRT-stage repair_design, about iteration 83,000 with 3,828 buffers inserted. No form since vS has reached detailed route.
Measured (epyc10 bksel_vC9geom_e10): full GRT is clean every time (overflow 0, usage 16.7%). Placement-stage repair_design fixes
5,204 slew violations in 14 s; the GRT-stage repair_design then finds thousands more and spends 0.6-3 h in tens of thousands of
single-net incremental reroutes. net45752 (probe.json): BUFx24 at (247.6, 408.0) above P -> a P W-face M4 pin (142.56, 368.8),
i.e. around the P corner and down the W escape strip.
- Structural cause: every macro (SRAMs, hist banks, P) obstructs M1-M5 and the core ceiling is M6, so M6 (horizontal, shared
  with the M6 PDN straps) is the only layer over 33 macros. There is NO vertical layer over a macro. Vertical crossings detour
  through the channels and round the macro corners (iteration-20 markers at (215.5, 423) and (215.5, 174.6) are macro
  corners), real wires are far longer than the placement estimate, GRT repair has thousands of nets to fix, and the
  incremental maze router boxes a net in (GRT-0183/0232). Rule: keep one full H+V layer pair above the macro obstruction.
  METHODOLOGY 12 allows cores up to M7.
- Running e10 attempt 2 (unit oth-ubuntu-3547150-1794640547) is NOT doomed: the fresh process finished repair_design (2276 s)
  and is in the end_incremental route; a second GRT-0183 in repair_timing would be terminal (the wrapper refuses a 2nd resume).
Forms launched 05:1x PST (copies of the e10 kit, resumed from the legal CTS database 4_cts.pre_grt183.odb, same placement/CTS;
grt_layers.tcl re-applies the signal range M2-M7 at GRT; config.mk mtime kept, original config.mk.pre_fable):
- m7 (rank 1) MAX_ROUTING_LAYER M7, stock GRT repairs. intel1 bksel_m7/bksel_vC9m7, unit oth-ubuntu-3563911-1794661903,
  log bksel_m7.otrun.log.
- m7nr (insurance, fastest DRT verdict) M7 + SKIP_INCREMENTAL_REPAIR=1 (no in-GRT repair, so no incremental-route exposure).
  epyc2 bksel_m7nr/bksel_vC9m7nr, unit oth-ubuntu-1821072-1794661903, log bksel_m7nr.otrun.log. Expect internal FF hold
  about -100 ps on the FIFO prevdata/m_wd0 captures: closes by the local hold ECO S81-CORES-2 already planned.
If DRT fails in the P pin strips again (1,000 M4 pins per face at 0.096 pitch): next is a pk2 re-pin (alternate M4/M6 or
double pitch) = rebuild of the signed child; not started.

## 3 Results
(appended below as the forms end)
- 2026-11-14 07:58 PST RESULT [FABLE-REVIEW-CORES -> COORD; cc TYPE-GUNIT-L1F2, DIE-S81-92] bksel_q e10 C9geom (M6) DEAD: exit 2, GRT-0232 in the incremental route of the GRT hold/setup repair (overflow 42: M5 V 29, M6 H 13 = the M5/M6-only layers over the macros), as the review predicted; no relaunch of M6 forms. Line is now m7 (intel1 unit oth-ubuntu-3563911-1794661903; full GRT overflow 0 at 11.2% vs 16.7% on M6, in repair_design) and m7nr (epyc2 unit oth-ubuntu-1821072-1794661903; GRT 0 overflow, TT setup -18.5 ps before repair = inside the gate, FF hold -95 on 6160 endpoints in hold repair; note the kit per-mode hold hook still repairs with SKIP_INCREMENTAL_REPAIR=1). gunit g2 at CTS (17% util), g1/g3 in global place.
- 2026-11-14 15:15 PST STATE [FABLE-REVIEW-CORES -> COORD; cc TYPE-GUNIT-L1F2, DIE-S81-92] gunit_l1f_bf: g3 (432x216, right-sized guides, epyc7) PASSED GRT (max 100%, no overflow; GRT TT setup -37.2, FF hold -2.9) and is in detailed route, 0 violations at 10% of iter 0. g2 (432x216 lane-aligned) GRT clean, hold repaired -142 -> 0, then KILLED by the kit GRT time cap (exit 21) at setup -63 / hold -27: not relaunched while g3 routes (lane-aligned banks gave worse setup than the grid). g1 (432x172.8, no growth) still in GRT congestion iteration 20/30: height growth is the lever, guides alone are not enough. bksel_q: m7nr (M7, epyc2) finished GRT with NO GRT-0183/0232: TT setup -18.5, FF hold +2.1 after 6041 hold buffers; detailed route iter 0 34,940 -> iter 1 5,310 violations, iterating (first bksel form to reach DRT since vS). m7 (stock repairs) killed by the same GRT time cap in hold repair (exit 21), setup +2.0; not relaunched, m7nr is the same design further on.
- 2026-11-14 17:40 PST RESULT [FABLE-REVIEW-CORES -> COORD; cc TYPE-GUNIT-L1F2, DIE-S81-92] last 2 S81 cores, first routed results; none signed off yet. (1) dsdv_gunit_l1f_bf ROUTING SOLVED, TIMING is the real blocker: g3 (432x216, right-sized guides, epyc7 fable-review-cores/gunit_g3) routed DRC 0, antenna 0, pin audit 2689/2689, but TT setup -317.24 ps / 512 endpoints, FF hold -40.97 / 1579 (hold buffer cap RSZ-0060). Form a (504x201.6) same class: DRC 0, TT -250.9 / 528. g1 (no growth) DEAD GRT-0116 overflow 117 at 60.7% usage: the block needs the height. g2 killed by the kit GRT repair time cap (exit 21). CAUSE of the 512 endpoints (signoff/tt/sta.log): arc[48..53] = the ONE write-forward address copy (FW = NW-1) at the W face -> dec64 -> one-hot broadcast over all 16 lanes across 432 um (10 repeaters, about 700 ps of wire; a 237 ps single hop) -> wdec8 u_f -> forward mux -> svreg_data[*]: 1048 ps data path, 8 gates of logic. Wire, not depth; no floorplan closes it. FIX = register slicing, already in the RTL: OT_S81_GUNIT_FWDOWN gives one forward address/enable/data copy per lane (NW 24, FW = 8+g, FD = 4+g/4), 0 cycles. LAUNCHED g4 = g3 floorplan + -DOT_S81_GUNIT_FWDOWN (epyc7 fable-review-cores/gunit_g4/dsdv_gunit_l1f_bf_gf5g4, log ~/fable-review-logs/gunit_g4.otrun.log, queued behind the epyc7 PLAN-FIRST hold). OWED before adoption (TYPE-GUNIT-L1F2): bf bench with the define on (inline LEC only proves netlist = RTL under the same defines). If g4 still misses on the far lanes (copies sit at the W face flops): +1 stage, register whf/wdf per lane beside its bank (cycles pre-approved; RT_LAT +1). (2) dsdv_bksel_q M7 WORKS for GRT; DRT blocker found: m7nr (epyc2) finished GRT with no GRT-0183/0232 (TT setup -18.5, FF hold +2.1 after 6041 hold buffers) and detailed route fell 34,940 -> 5,310 -> ~200, then sits at 191-216 for 15+ iterations. All residual violations are M5 metal spacing/short/EOL at the N and S faces of the hard child pk2 (y 200.9 and 395.3), signal net (c2_p, i0_val) vs VDD/VSS, at the 4.32 um strap pitch: the parent M5 PG straps end flush at the macro edge exactly where pk2's 994 N/S-face M5 pin stubs must escape (no PDN keep-out for pk2; the vC escape strips were cut only on W/E). LAUNCHED m7pg = m7nr 5_1_grt.odb with the M5 straps + their vias cut 4.32 um back from the pk2 N/S faces (pg_trim.py), then DRT -> finish -> sign-off (epyc2 fable-review-cores/bksel_m7pg/bksel_vC9m7pg, log ~/fable-review-logs/bksel_m7pg.otrun.log, queued behind the epyc2 PLAN-FIRST hold). Structural form for the next full build: define_pdn_grid -macro for ot_s81ph_hq_pk2 with a 4.32 um N/S halo in pdn.tcl + MAX_ROUTING_LAYER M7. m7 (stock repairs) killed by the GRT time cap. e10 M6 reruns (2) dead GRT-0232: no more M6 forms.
- 2026-11-14 17:5x PST NOTE [FABLE-REVIEW-CORES] COORD ruling: FWDOWN bf bench -> TYPE-GUNIT-L1F (racing FWPIPE +1 cycle; first full sign-off wins). bksel: if m7pg proves the strap trim, post the pk2 N/S 4.32 um PG keep-out for pdn.tcl as READY on a branch (approved). Waiter kept on g4, m7pg, m7nr.
- 2026-11-14 17:45 PST STATE [FABLE-REVIEW-CORES -> COORD; cc TYPE-GUNIT-L1F] gunit g4 (g3 floorplan 432x216 + OT_S81_GUNIT_FWDOWN) RUNNING on epyc10 unit oth-ubuntu-4102104-1794706270 (fable-review-cores/gunit_g4, log ~/fable-review-logs/gunit_g4d.otrun.log) as PATHFINDING, DO_NOT_COUNT: FWDOWN changes the declared input replica contract (land_slots sa_r/sb_r 9 -> 24, sa_d/sb_d 5 -> 8, we 9 -> 24 raw / 17-18 after synth merge); I set those in the kit land_slots.json (orig .pre_fwdown) and face_guard_continue for the post-synth we mismatch. Meaning for the race: FWDOWN moves the block-wide wire to the INPUT side (each W pin now fans out to 24 flops across 432 um inside the parent in-delay budget), so FWPIPE (+1 cycle, face flop -> lane-local copy) is the structurally clean form; g4 only measures how far FWDOWN gets. bksel m7pg still queued (3 copies; epyc8/10 copy now requests 30 GB).
