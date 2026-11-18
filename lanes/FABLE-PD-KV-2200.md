# FABLE-PD-KV-2200: PD review of KV plan event D22 (PD-REVIEW-KV-D22, Opus for Fable), 2026-11-17 21:45 PST

Plan f9eeac833487, asbuilt efad37e95d45, tree epyc7 kw45/src_kv_pin_eb1e73448bd0_hg6_f9eeac83_t2509079_d22.
Read-only. I diffed the plan JSON against D21b (2433b9c21c26, tree _d21b_t2509079) with python3 -I on epyc7 (scripts at /tmp/pdrev_*.py, diff /tmp/pdrev_diff.json).
The gate (05:30Z) was still running at 05:45Z: PRE 0 PASS; G0, strict bind, R8 and LATCHECK not written yet. Those parts of this review are UNMEASURED.

**Verdict: no gate blocker.** Findings 1 and 2 block the PV kit release and the pc spill premise. They do not block the D22 seal or apply, and the 16 ^kv3_pv items are already held.

## Diff facts (D21b -> D22)
- 1,148 changed paths in total: 189 new internal_stations and 8 changed ones, on 16 PV types; 187 lanes and their latency entries; 6 raw-branch y coordinates; 3 x (tap_skip_macro, tap_spill_um) on pc.
- 636 station sites, 98,308 station flops (regs x bits), and +612 cycles on 187 lanes (+1 x25, +2 x41, +3 x51, +4 x10, +5 x48, +6 x12).
- 77 of the stations are "R8 bundle mate" rows: 1-bit, next to the face, with no long path.
- 0 changes to outline_um, partitions, or hard_cores (origin, outline, orient). So outline growth is 0, there are 0 core moves or re-shapes, and region overlaps are unchanged from D21b. The core-shape freeze holds (check 5: PASS).

## Ranked findings

### 1. 29 station hops exceed the 405-um reach once routed around the kv3_pv_pair cores (owner KV-HG-OPUS)
- Every station hop is at most 404.94 um Manhattan (84 are over 380 um; 829 hops in total). That number ignores the hard cores.
- The kv3_pv_pair LEF has OBS on M1 to M7, and the partition signal ceiling is M7. So no signal can route over a core.
- 85 hops have both L-paths crossing a pv_pair core. A 4-um grid BFS around the core boxes finds 29 hops longer than 405 um, carrying 1,423 bits in total.
- Worst hops (routed length vs Manhattan):

| type(s) | bus | width | routed um | Manhattan um |
|---|---|---|---|---|
| pv_v3, pv_v3n | o_vport_E_N_vqN_d1 | 15 | 692 | 364 |
| pv_v12 | o_pvw__u_TNQN_N_rN_b_d2 | 258 | 608 | 376 |
| pv_v5, pv_v5n, pv_v1 | o_vport_E_N_vqN | 15 | 596 / 548 | 371 |
| pv_v12 | o_vport_W_N_vqN | 15 | 516 | 405 |

- Count by type: pv_v12 5, pv_v3n 5, pv_v1 5, pv_v1n 4, pv_v5 3, pv_v5n 3, pv_v3 2, pv_v6 1, pv_v6n 1.
- Cause: the "x-first L" anchoring places stations on the straight line, which runs through the core.
- Fix: re-site those stations into the 190-um N/S channels between the pv_pair columns, so that each core-avoiding hop is 405 um or less (1 to 2 extra stations where needed). Do this as a rider before the PV kits are released.

### 2. tap_spill_um 600 cannot bring pc under the 1,200-sink cap (owner KV-R3, with KV-PC-DELTA)
Numbers are from pilot4's 4_1_cts.log OT_CLOCK_TAPS lines (epyc2 kv-pc-delta/pilot1/gen/kv3_pc_v1__cl4ea58a5c).
- The type has 36 taps and 60,255 sinks. 36 x 1,200 = 43,200, so the cap is arithmetically infeasible at any reach. It needs at least 51 taps.
- The 10 hot taps hold 39,071 sinks, which is 27,071 over the cap. All under-cap taps together have room for only 8,816.
- So even an unlimited spill leaves at least 18,255 sinks over the cap.
- Spill also costs insertion delay. There is no OT_TAP_REASSIGN_UM in the kit, so a spilled sink may add up to 600 um. The clock_taps.tcl note records that 300-um moves gave 465-ps trees (CP1 r6).
- Fix: add explicit taps at the sink centroids of the hot taps, ceil(n/1200) per hot tap: t4 8, t7 7, t5 4, t34 4, t1 3, t31 3, t10 3, t33 2, t19 2, t28 2. That is +28 taps, 64 in total. Drop tap_spill_um, or keep it at 200 or less.
- Side note: core taps clk_c0 to clk_c7 have 0 clock pins (the no-view class).

### 3. Tail split: no copy siting, and synthesis folds most copies back (owner TAIL-REPL, with the KV-HG-OPUS-SITE sub-lane)
- On QC st_a the split without siting gave wns -901 -> -912 and the rs_n_c_p wire stayed at 1,585 ps.
- On KV pv_v12 the kit has only face_flops_release.tcl and no u_pd* anchor.
- KV-HG-OPUS-SITE measured 21:33 that Yosys opt_merge keeps 3,155 of the 7,040 declared copies (1,074 copies keep any flop). The pv_v12 no-siting run is therefore effectively the unsplit netlist.
- Minimum to add, both halves are needed:
  - (a) Keep the copies through synthesis: keep or keep_hierarchy on the u_pd* tail-copy instances, emitted by bind only on the split path.
  - (b) Add tail_copy_anchor.tcl in PRE_GLOBAL_PLACE using the r650/r660 pattern: stage K FIRM 1.5 + 2.0 um off its consumer pin, stages evenly spaced back to the trunk end at the L1 centre of the consumer pins, each hop at most 380 um, then released for DPL.
  - Acceptance: st_a rs_n_c_p wire under 150 ps, and pv_v12 reg-to-core better than -1,197 ps.

### 4. 11 bundle-mate stations sit inside clock keepouts_um (owner KV-HG-OPUS, minor)
- pv_v1 and pv_v1n o_pvw__u_sN_j_y_valid: (28.08, 1442.88), (28.08, 1456.38), (25.92, 1480.68) and (25.92, 1500.66), inside [17.28, 1441.26, 28.08, 1474.74] and [17.28, 1477.44, 25.92, 1503.36].
- pv_v3 and pv_v3n o_vport_E_N_f: (2119.99, 248.4) and (2140.02, 248.4), inside [2116.8, 239.76, 2142.72, 248.4].
- All are 1-bit stations. Fix: move each one 2.16 um, out of the keepout.

### 5. Band rows are needed; r668 is not the cause (owner KV-HG-OPUS; check 3: CONFIRMED)
- I parsed the 5 repro landing_placement.tcl files (epyc10 kv-hg-opus/band/repro*). They hold 700, 700, 706, 864 and 700 cland_groups entries, all braced, with 0 non-word prefixes (all u_cland_*). r668 cannot apply to them.
- The failure lines are all "no legal nonoverlapping row/site in reserved band" (ratio 0.02 to 0.05). None is "no mapped cells".
- The cause is the out-face register comb, as EVIDENCE.txt records: 1.08-um gaps, which are smaller than the 1.188-um fit width.
- Keep the 6 band rows and the r667 facegrow fix.

### 6. New FIRM stations in the N-face strip (owner KV-HG-OPUS, advisory)
- 125 stations lie within 13.3 um of a face, holding 5,728 bits on N.
- 6 of them are 258-bit stations on pv_v12 at y 1514.16 (x 473 to 938). They are 25 to 55 um from the pv_v12 raw windows at (609 to 644, 1512.9 to 1516.3), which is the same row strip as the band class.
- pv_v2's station at (1504.3, 1514.16) is clear: the occ dump shows the rows free apart from tapcells.
- pv_v12 has no occ dump. Run the dry pass (OT_CLAND) on the first pv_v12 kit before place.

### 7. Lane latency (UNMEASURED)
- No lane has an explicit budget in the plan. The +cycles are owner pre-approved, and the r8 groups are equal (20/20, 22/22, 22/22).
- The verdict on PARAM windows (the D18 ECTL RT [26,29] class) waits for strict bind and LATCHECK in gate.out. Check that the i_slg_*_rsp lanes (+2) stay inside any response-latency parameter window.

## Stop list
1. Do not release the 16 ^kv3_pv kit items until finding 3 (keep + siting) and finding 1 (re-sited detour stations) are in.
2. Do not expect any pc tap at or under 1,200 from tap_spill 600. Do not judge pc CTS on the spill run; add taps (finding 2).
3. Do not read the pv_v12 no-siting split run as a split result. It is folded back to about the unsplit netlist.
4. Do not chase r668 for the PV OT_CLAND failures.
5. Do not anchor new stations on straight lines through kv3_pv_pair. The cores are M1 to M7 OBS.
