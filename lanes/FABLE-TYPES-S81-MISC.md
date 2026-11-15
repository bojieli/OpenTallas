# FABLE-TYPES-S81-MISC 2026-11-14 19:55 PST: unclosed S81 types outside leaf / col

Scope: slice_station beyond t29/t28/t36/t27/t47, dsdv_slice_*, serdes__t*, seqhost, iqf, eng, kv_leaf, svc_lo, gunit / bksel / xs4, phy. Read-and-diagnose from live kit logs, CTS reports and congestion reports on the build hosts. Nothing was killed, changed or launched. This adds to FABLE-WAVE-REVIEW and FABLE-HARD-S81 only what is new.

Status of each statement: MEASURED = read from a log or report today; INFERENCE = fits the numbers, not proven.

37 types with a physical problem on record were reviewed: slice_station 14, serdes 9, dsdv_slice 7, iqf, eng, seqhost, kv_leaf t1 / t5, phy, plus gunit / bksel / xs4 by reference.

## 0. Three results that change today's picture (all MEASURED)

1. **slice_station t8 form c is routed with DRC 0 and TT setup +136.98 ps; only the FF hold check did not run.**
   - Kit: epyc10 `/srv/opentallas-scratch2/claude/typeslicet8/c/slice_station__t8`. Pin audit 7468/7468.
   - `signoff/ff/sta.log` stops after `SO CELLS 6050876`: the FF STA process died with the host at 952 of 1007 GB. `signoff.json` says `hold_ff: NOT RUN`.
   - A rerun started 19:12 (`t8c_r2`, container `dpkit-slice_station__t8-2032908`). If it restarts the flow instead of only the FF corner, run the sign-off alone on `6_final.odb` with 64 GB.
2. **The wave now passes GRT on the old landing bands.** The automatic retry `GRT-EDGE auto` (`OT_GRT_TRANSITION_MODE=edge_outline`, log line `GRT-9103 ... edge_outline (K=2 gcells)`) gave Total overflow 0 in 1-2 extra iterations on kits that still have the 9.99-um strip, density 0.5, M8:

   | type | kit (ot-jobs dir) | GRT | hold at GRT | detail route at 19:40 |
   |---|---|---|---|---|
   | t36 | intel2 `slice_station__t36-route-...-1794690532` | 0, 6.90 % use | -5.79 ps, 2 endpoints, repaired | iteration 0 at 80 %, 73,246 violations, 36.6 GB |
   | t37 | epyc9 `slice_station__t37-route-...-1794694202` | 0, 6.93 % | -16.15 ps, 65, repaired | iteration 0 at 80 %, 57,106 |
   | t43 | epyc9 `slice_station__t43-route-...-1794701813` | 0, 6.76 % | +1.63 ps | iteration 0 at 60 %, 49,543 |

   - This corrects FABLE-HARD-S81 section 1 ("any further wave attempt of t27 / t28 / t36 on the old bands is a dead end"): true for GRT without the edge mode, not with it.
   - It is not yet a sign-off. t49 took the same path and died in detail route: `DRT-0255 net ft2_i[324]` at (413.82, 1219.80)-(417.81, 1223.79), on the N landing face. Form c of t37 (density 0.35, M9, grown outline 1442.88 x 1356.48) had 22,658 violations at 50 % of iteration 0 against 40,755 for the M8 / 0.5 kit at the same point.
   - So the three builds above are the test of whether the landing face survives detail route without the densify. Read their end before launching more forms.
3. **dsdv_slice_iq_C__t1 has a 39-hour route job that cannot finish.** epyc8 `dsdv_slice_iq_C__t1-route-outgoing-giraffe-1648380-1794571318`: cell census at CTS 1,412,086 non-tap cells, 2,143,712 projected with wire repeaters. GRT is at extra iteration 10 and its log has not moved since 15:00 PST. Nothing above 517 k has ever closed.

## 1. serdes (t1, t2, t3, t4, t12, t13, t14, t15, t16): routing is clean, three clock and timing structures fail

GRT is not the problem: Total overflow 0 at 2.5-3.5 % use on t12, t14 and t16 (wave kits, density 0.25, M8). Every live serdes route is stuck in timing repair inside GRT.

| type | kit | setup after CTS | hold at GRT start | repair state at 19:35 |
|---|---|---|---|---|
| t12 | intel2 `serdes__t12-route-...-1794701049` | -309.2 ps, 7 endpoints, `u_dec.u_syn.am_ok` | -248.94 ps, 2,076 endpoints, TNS -126,927 | 690 buffers, WNS fixed at -163.619 for 350 iterations, endpoint `u_dec.u_chn/k_lo[208]` |
| t14 | epyc2 `serdes__t14-route-...-1794693518` | -454.9 ps, 340 endpoints, `u_txl.q -> u_ptx/d` | -223.60 ps, 2,674 endpoints | 733 buffers, WNS fixed at -173.511, endpoint `u_dec.u_face_p_d.q[12]/D` |
| t16 | intel2 `serdes__t16-route-...-1794701066` | -190.6 ps, 55 endpoints, `u_dec.u_syn.xs[0][1]` | not reached | setup repair at iteration 1090, no gain |
| t2 (11-13) | epyc9 attempt_27 | unmeasured | -180.60 ps | 6-h cap at 656 buffers, WNS -101.530 on `u_chn/k_lo[225]` |

### Cause A: the recovered clock is one port-rooted tree, 1.9-2.2 ns deep (MEASURED, t12 `4_cts_final.rpt`)

- `io_pma_rck[0]` drives 22,306 register sinks and 5 macro sinks (`4_1_cts.log`). Ten max-wire repeaters sit on the clock net before the tree root (0 to 591 ps). Clock arrival at the launch flop `u_dec.u_lpl_2_r.o[208]` is 1,876 ps.
- The macro branch carries a chain of more than 41 `delaybuf_N_io_pma_rck` cells (about 22 ps each) and reaches `u_dec.u_chn/clk` at 2,046 ps, 170 ps after its launch flop.
- The `ot_s81_kp4_dchn` view asks for 174.59 ps of hold on `k_lo`. Slack: -293.93 ps. The view is `legacy_etm_max_bound`, `signed: false` (kit `core_latency.json`, declared insertion 315.1 ps).
- Hold repair cannot fix this endpoint: on t12 the worst slack did not move in 350 iterations and 690 buffers. The same endpoint class ended t2 at the 6-h cap.
- t14 shows the other face of the same tree: PMA receive data into the face flops, -173.5 ps and fixed (SERDES-TXPIPE measured 2,175 ps insertion at those flops).
- INFERENCE: the balancer delays the macro branch to match the register tree and overshoots, where the macro needs its clock earlier than the registers by its hold time. The view does carry `max_clock_tree_path`, so why the chain is that long is not explained.

### Cause B: the sink cap splits the encoder pipeline across two taps (MEASURED, t12)

- `OT_CLOCK_TAPS cap 3000 sinks/tap: 2419 sinks re-assigned`: tap `clk_t10` had 5,419 sinks and was cut to 3,000; `clk_t11` went from 62 to 2,074.
- Worst register-to-register hold: `u_enc.d1[254]` on `clk_t10` (arrival 104.99 ps, source latency -66) to `u_enc.d2[254]` on `clk_t11` (arrival 279.24 ps, source latency 0): -156.66 ps. 2,014 hold violations after CTS.
- The cap is `OT_TAP_MAX_SINKS`, default 3000 (`clock_taps.tcl` line 223). The owner deleted sink limits on 11-14; this one is still in the kit.

### Cause C: the receive cone defines are not in the wave bind (MEASURED)

- t12 `config.mk` carries only `KP4_DEC_HARD`. The cone set that HARD-S81-SERDES-1 proved on 11-13 (RST_TREE, RM_STAGED, RM_LOCAL4, RM_WFULL8, KP4_SYN_LOCAL, KP4_AM_FACE3, CLAND_WCHK) is absent, and so are TXPIPE / RXPIPE.
- That is the -190 to -309 ps on `u_syn` in t12 and t16, and the -455 ps transmit path in t14.

### Dead ends

- Waiting on the t12, t14 and t16 routes: hold is fixed at -164 to -174 ps and setup at -190 to -455 ps. They end at the time cap.
- More repair time (t2A, `OT_GRT_POST_MAX_S=43200`), lower density (t2B, t4B) and sparse utilisation (t14 B2): none touches the clock.
- t4B (intel1, density 0.15) did repair hold (-73.18 ps, 310 endpoints, 253 buffers) and is in detail route at 60 %. It still has 20 setup endpoints unrepaired; read its sign-off before copying the form.

### Fix: one serdes event (DIE-S81-92, with TL-SERDEST14 and SERDES-TXPIPE)

1. Recovered-clock island: all `io_pma_rck` sinks in the island under the PMA with the tree root at the island, as in the HARD-S81-SERDES-1 template (kitH2 placed, local density 0.808). Target insertion a few hundred ps instead of 1.9 ns.
2. `u_chn` on its own early tap: clock at the macro pin no later than register arrival minus 175 ps. No balancing chain on the macro branch.
3. Tap assignment by pipeline group: every stage of `u_enc` on one tap. Remove the 3000-sink cap or raise that tap; never split one pipeline between taps.
4. Bind defines: the proven cone set plus TXPIPE / RXPIPE with the stage counts SERDES-TXPIPE posted at 19:00.
- Proof in one build (t12, to CTS only, about 3 h): in `4_cts_final.rpt`, `u_chn/clk` arrives at least 175 ps before `u_lpl_2_r` flops; no `u_enc` path crosses taps; hold violations after CTS fall from 2,014 to tens; `am_ok` setup is not negative.

## 2. Landing ring at the pin face, outside slice_station: iqf__t1 and eng__t1 are not in the densify

- iqf__t1 (epyc9 `iqf__t1-route-...-1794692055`, 194,319 cells, no macros, M8, density 0.5): GRT is in its second round at extra iteration 14. Overflow by report: H 5,300 / V 17,211 (iteration 15), H 753 / V 19,137 (5), H 4,670 / V 17,197 (10). It does not converge.
  - All of it lies at the N face, y above 1080. Vertical overflow sits at x 240-600 (13.6 k of 17.2 k) and x 960-1080; horizontal at y above 1200.
  - More than 95 % of the nets in congested gcells are ring nets of `u_cland_ft*_i` and `u_cland_ql_i*`.
  - Three landing windows abut: ft6_i x 232.16-343.07, ft7_i x 344.67-455.58, ql_i0 x 461.02-569.45; 2,885-2,890 ring flops each in a strip 9.99-10.26 um deep, 4.6 bits/um. This is the t36 pattern of FABLE-HARD-S81 (three abutted windows above 4.5 bits/um), at 20 times the overflow.
  - The kit has no edge mode (no `GRT-9103` line).
- eng__t1: GRT-0116 again at 17:02 (16001bfa2df5); FABLE-WAVE-REVIEW measured 36,705 overflow, 88 % ring nets. The wave set the edge mode for its next attempt at 17:27.
- The S81-LEAF-PLAN densify covers slice_station (143 bands, 44 types), col (40 bands) and leaf / kv_leaf. Its handoff names eng__t1 and bk_sel__t2 once (tap offsets) and iqf not at all.
- Dead end: the running iqf route, and any retry of iqf or eng on 10-um strips without the edge mode.
- Fix (S81-LEAF-PLAN, in B6): run `leaf_rules bands --densify --per-bit 10` on iqf__t1, eng__t1, seqhost__t1 and bk_sel__t2 as well, and leave a gap between abutted windows. Side A/B meanwhile: relaunch iqf with the edge mode, which costs one GRT.
- Proof: iqf on the densified bands, GRT Total overflow 0 without allow-congestion.

## 3. slice_station t8, t22, t24, t25, t26, t37, t40, t41, t42, t43, t49, t52, t6

- One class, already diagnosed (FABLE-WAVE-REVIEW S1, FABLE-HARD-S81 section 1): ring cells in a 10-um strip at the landing face. New GRT-0116 ends today: t25 (16:42), t42 cl4bd1432c (18:03), t26 (18:45).
- What is new is section 0: the edge mode clears GRT, and detail route decides.
- t37 form a (allow-congestion on the old kit) ran 5.5 h and ended `EST-0104 inconsistent parasitics state`: the kit predates the WAVE-FRICTION-1 catch of 15:00. Do not copy form a onto kits generated before that.
- t8 form b (density 0.4, M8): GRT-0116, Total 3,077 after 30 iterations. Density alone does nothing.
- t41 (11-12): routed, DRC 0, TT +51.05, FF hold -66.78 ps. It has no pre-GRT hold; its new attempt is in placement.
- Order of work: (1) finish the t8 FF check; (2) read the detail-route end of t36 / t37 / t43; (3) if they die on DRT-0255 at the face as t49 did, the path is PG-AWARE-1 (proof build `pg-aware-1/proof/ss_t49` on intel1) plus the B6 densify, and no more old-band attempts; if they finish, set the edge mode as the family default now and keep the densify for the next event.

## 4. dsdv_slice_*

### Placement that does not converge: lepw_mu_C, lepw_mus_C, c1x t7, kv512 (MEASURED on lepw_mu_C)

- intel2 `dsdv_slice_lepw_mu_C__t1-place-...-1794657902`, 15 h in global placement: 284,991 movable cells at 3.456 % utilisation, target density 0.5, 2048 x 2048 bins, routability-driven and timing-driven.
- Overflow stalls at 0.21-0.26 from iteration 4,370 on, while wirelength goes from 2.70e7 to 1.14e8 to 1.30e8 um. That is divergence, not slow convergence. It ends as GPL-1010 at the pass cap, as c1x t7 did (iteration 9,720, overflow 0.253) and kv512 (8,830, 0.264).
- The kit prints `OT_GPL_SPARSE movable util 3.024 % (threshold 2.000 %): GPL modes unchanged`. The sparse mode, which drops routability-driven placement, starts only below 2 %; these types sit at 3.0-3.5 %. TL-SERDEST14 placed serdes t14 with the threshold raised (`OT_GPL_SPARSE_UTIL=0.9`).
- INFERENCE: routability inflation on a 3 % design is what diverges. The 20 % of area that never spreads could also be cells fenced in landing bands; not separated.
- Fix (KIT-OPS-5, class setting in gen): sparse threshold 10 % for S81 partition types. Proof: lepw_mu_C placement converges below overflow 0.10 in under 1,500 iterations with flat wirelength.
- Dead end: the lepw_mu_C and lepw_mus_C placements now running, and unchanged relaunches of kv512 and c1x t7.

### c1x_C__t8: real overflow at the S face (MEASURED, 11-12 kit, M7 top)

- epyc9 `/srv/opentallas-scratch2/claude/vl3s/b/C1/dsdv_slice_c1x_C__t8/gen/dsdv_slice_c1x_C__t8`, cancelled 18:35 after 25 h in GRT. `congestion-5.rpt`: H 45,725 / V 31,934; 2,755 congested gcells have capacity 0.
- Horizontal overflow sits at x 240-720, y 0-360 (33 k of 45.7 k). Nets: repeaters, `u_ist_leafdn_o*` frames (67 k hits) and `u_bout_leafdn_o*`.
- The macro `u_lp_u_xr` is at (449, 69), directly above the landing window `leafup_i2` (pins x 373.66-513.57, 3,385 ring flops in a strip 4.59 um deep, 249 columns). `u_lp_u_cap` at (35, 35) is the same pattern at the SW corner.
- This is the leaf class of FABLE-HARD-S81 section 2: a hard core in the slot between a landing face and its logic. The kit is two days old and M7; current kits are M8, so the amount will differ. INFERENCE that the cause holds.
- Fix (DIE-S81-92 with TL-SLC1XT8): no core within 86.4 um of a landing window on that face; move `u_xr` north, or move the `leafup_i2` band beside it. The fC street-rule plan is the right vehicle; fA / fB on the unchanged plan are not.
- Proof: GRT of fC; no congested gcell with capacity 0 at x 240-720, y 0-360.

### iq_C__t1: oversize (section 0, item 3)

- Dead end: the 39-h route on epyc8 and the place job on epyc7. Fix: OVERSIZE-1 split or hardened engine; cancel both jobs through the watchdog.

### DRT-0073 on hard-core clock pins (lep*, 4 builds in FABLE-WAVE-REVIEW class H)

- Same defect TYPE-GUNIT-L1F2 measured on gunit: the abstract has an 84-nm pin sliver under a blanket obstruction. Its tool (`~/gunit-lef-fix/finish_lef.sh`) is the fix. Apply it to the lep core views (S81-CORES-2). Not re-measured here.

## 5. kv_leaf t1: structural hold at the feed-through stations (MEASURED)

- intel1 `ot_s81sl_kv_leaf__t1-route-...-1794681285`: GRT Total overflow 0 after 14 iterations at 6.32 %.
- Hold at GRT start: -215.65 ps on 8,448 endpoints, TNS -418,951. Worst endpoints `u_ft_ft4_o_2/q[*]/D`. After 150 iterations: 498 buffers, WNS -159.8.
- The kit has no `OT_PREGRT_FF_HOLD`; kv_leaf t5 has it. At about 8 buffers per endpoint this needs roughly 70 k buffers; it will run to the time cap.
- INFERENCE: station flops of one feed-through sit on taps with different insertion, as in serdes cause B. The launch and capture taps were not read.
- Dead end: the running t1 route. Next step (S81-LEAF-PLAN / TL-KVLEAFT5): read the worst hold path in `4_cts_final.rpt` for the two tap names, then put both station rows of a feed-through on one tap. Pre-GRT hold is the bridge, not the fix.
- kv_leaf t5 (epyc9): GRT overflow 0; wire repair at 136,000 of 320 k nets with no log line for 2 h. Watchdog case, no design finding.

## 6. No new physical finding

- seqhost__t1: LEC verdict is an artifact (TYPE-SEQHOST-LEC). Setup before CTS was -247 ps on 3,863 endpoints (`u_win.armed`); the LA 4 define exists. Attempt 13 entered route at 19:16. It also needs the section 2 densify.
- svc_lo rs t1-t7, rs_w: no build has reached placement. svc_lo rs t2 has sat in the yosys SHARE pass since 12:35 UTC (intel2). Same RTL and same cause as svc hi: FABLE-HARD-S81 section 4, fix in B6 (`OT_SVC_ATT_MEM_MACRO`).
- gunit, bksel: FABLE-S81-CORES is live on both (g4 in GRT, m7pg in detail route). xs4: three TYPE-XS4 forms running on epyc10, the oldest for 17 h; not read.
- phy__t1: hard IP, not counted. The exit 241 was the memory killer at 33-37 GB (ADMIT-TUNE-1).
- dsdv_slice_c3x_C__t1, c1x t1 / t3 / t5 / t9 / t10: only infra ends on record.

## 7. Dead ends in one list

- serdes t12 / t14 / t16 routes in GRT repair; t2A; any serdes build without the clock event.
- iqf route (GRT round 2, 22 k overflow); eng on 10-um strips without the edge mode.
- slice_station form a on kits older than 15:00; form b.
- lepw_mu_C / lepw_mus_C placements; kv512 and c1x t7 relaunches at the 2 % sparse threshold.
- c1x t8 fA / fB; iq_C route (39 h) and place.
- kv_leaf t1 route (8,448 hold endpoints at -216 ps).

## 8. Not done

- No STA what-if was run: hosts were at 950 of 1007 GB. The serdes proof (shorten the macro delay chain on the saved t12 `4_cts.odb`) is the first one to run.
- Why the macro branch of `io_pma_rck` gets a 41-cell delay chain although the view has insertion data.
- kv_leaf t1 tap names of the worst hold path.
- Detail-route end of t36 / t37 / t43; sign-off of t4B.
- xs4, and the current M8 kit of c1x t8.

Evidence: kit paths as cited. One helper was left on epyc9, `/tmp/fable_s81misc_cong.py` (congestion report binned by region and net family, read-only); it can be deleted.
