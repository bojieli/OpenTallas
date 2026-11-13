# QC-S28-F (DIE-QC-99 s28 event, lane F) — su station reach, sle_ctl reach, st streets, FW E-face

Base: plan_qc99_s28 `2f0c17d5f1a3` (claude/qc-event-s28-1111@88018018ef), sidecar `38a30992accc` (unchanged).
Delta: `delta_s28f.json.gz` (json sha256 `602460a635b7`), 18 ops, 6 types, 0 die keys, 0 sidecar ops.
Result: plan `0de51c426842` (apply output byte-identical to the composed plan).

```
gunzip -k delta_s28f.json.gz
python3 -I scripts/apply_s28f.py apply plan_qc99_s28.json delta_s28f.json OUT.json --report R.json   # three-way, CONFLICT exit 3
```

Touched (only): `partition_types[T].clock.landing_contract.bands.<monitor_i>.{rect_um, max_pin_to_band_hop_um, placement}`
for T = slw_su_l1__clcc9d0155, slw_su_l1__cla2a78701, sle_su_l1__cl5ea486db, sle_su_l0__cl7a55c676,
slw_su_l0__cl1e5219ea, slw_su_l0__cl76fb247e.  No cb*/cbx/sl_sc/B-street/coll*/glue/native59 type, no strip re-pitch.

## F1 su lanes — class MONITOR-BAND-SITE (fixed, 0 cycles)
The OPEN slw_su_l1 monitor ring (-161.2 ps, WRITE leg cland_dn_fault_0 -> u_cland_monitor_0) is a plan site error, not a
cycle problem: monitor_0's band was copied from sibling cla2a78701 whose collector children are in another order, so the
band sat on the S face 450 um (pin -> far corner) from its own status pins on the W face (recorded 217). Same class in 5
more su bands. Fix (scripts/monband_s28f.py): the same band (w x h, flops) moved next to its 3 pins (ready/fault/fclk),
legal = in-outline >= 6.48 um, clear of every hard core, other band, ft/station register, local reset and anchor relay.

| type | band | old rect | pin->band (true) | new rect | new |
|---|---|---|---|---|---|
| slw_su_l1__clcc9d0155 | monitor_0 | 250.56,19.44,298.08,28.08 | 450.4 | 6.48,146.88,15.12,194.4 | 40.0 |
| slw_su_l1__cla2a78701 | monitor_0 | 250.56,17.28,298.08,25.92 | 163.0 | 136.728,17.28,184.248,25.92 (clcc9d0155 monitor_1 precedent) | 49.2 |
| sle_su_l1__cl5ea486db | monitor_0 | 17.28,628.56,64.8,637.2 | 195.5 | 6.48,483.84,15.12,531.36 | 40.0 |
| sle_su_l0__cl7a55c676 | monitor_1 | 557.28,1030.32,604.8,1038.96 | 210.6 | 606.96,1153.44,615.6,1200.96 | 40.0 |
| slw_su_l0__cl1e5219ea | monitor_1 | 557.28,710.64,604.8,719.28 | 195.5 | 606.96,816.48,615.6,864.0 | 40.0 |
| slw_su_l0__cl76fb247e | monitor_0 | 557.28,710.64,604.8,719.28 | 195.5 | 606.96,816.48,615.6,864.0 | 40.0 |

The priced fallback (clock.landing_monitor_freg -> FREG=1 on u_cland_monitor_i, +1 boot-status cycle, seam transport
3 -> 4, tool + schema change) is NOT needed once the band sits at its pins (a 40-um leg).

Reach (hops > 405, station ends 33-132 um off cores): no violation. pb_reach.py mirrors the kit TCL per bit (is_bits +
is_knee_site, start_um for start_core chains, plus the unregistered lane-pin leg from the bound RTL concatenation): 364
per_bit chains on the 9 su types + sle_ctl__cl67434795 -> max kit knee 395.7 um, max true hop incl. lane leg 395.7 um,
0 > 403 (evidence/pb_reach_base.tsv).  The die-view audit's >405 / "stale ends" read the representative regs_um
centroid line and the SU-RS-1 clear-leaf/spread leaf_um; fix the audit, not the plan.
1.3-um core street on slw_su_l1: the sliver is between landing macros cl_rsf_i (E face has 0 pins) and cl_flt_su_c_i
(W face 12 pins), street_V p99 0.55 -> not a routing hot spot; moving a hard landing breaks its rsf ft bit_sites
(4 x 515 explicit sites at x 559-581). Cosmetic, no change.

## F2 sle_ctl__cl67434795 — no change
x_hc1/2/3_i kit knees 383.5 / 384.7 um (< 403), true hop incl. lane leg <= 395.7; route_supply p99 1.094.

## F3 st_a / st_b streets (11 types not in S28-B) — no change, numbers
sle_st_a_v1 x3, sle_st_a_v2, sle_st_b_v1 x2, slw_st_a_v1__clb036e152, slw_st_a_v2 x2, slw_st_b_v1__cle6023ec2,
slw_st_b_v2__pvc2ec5bfb: route_supply has no street region over threshold (ring p99 0.852-1.023, mem 0.24-0.82); the flag
is dens_A 1.01-1.19 = area, i.e. outline growth = lane E's strip re-pitch scope.

## F4 FW-EFACE-BIN — gap (tool form), tap cap trial rejected
LAND-RING-2 pilot slw_fw_v1__cl51d45468 (congestion-5.rpt): fill 0.048, all E-face bin/bout flops in a 4-10 um column
x 600-613, H gcells cap 24 vs use 25-27 (u_bin_x_fe_p1_i / x_fe_i / u_bout_x_ctl_p1/p2), E face 2872 in + 3833-4091 out
bits.  Cause: face_flops.tcl fixed column pitch ff_cpitch = 40 sites (2.16 um), rows +-2 at the pin row; no plan key.
Structural form = tool change (per-type face-flop band depth / pitch key, e.g. clock-free E-face band 20-30 um deep)
or move x_ctl_p1/p2_o off the E face (die port change).  Hand to QC-FW-FORMS (claude/qc-fw-forms-1111 6d2e3de5ff, never
READY; covers slw_fw_v3, slw_fw_v1__clc7ddab13, sle_fw_v3) + a FLOW tool owner; not duplicated here.
Tap cap: sle_fw_v2__cl69f5e854 clk_t63 1245 / sle_fw_v3 clk_t27, t54 1243 (cap 1200, +3.7 %).  tap_target_sinks 900 ->
800 clears it (max 898 / 1058, G0 tapcap 77 -> 73 taps, 39 -> 37 types) but, after collector_reattach, regresses reset
collector reach (sle_fw_v3 sc_ei 57 -> 397 um, cmd_ei 88 -> 239; sle_fw_v2 cmd_ei 55 -> 230) and orphans the
group_rects_um overrides u_cland_collect_rst_n_t17 / _t38 (G0C geom_clock_reach "not evaluable").  Rejected
(evidence/taptarget_trial_rejected.json, scripts/taptarget_s28f.py); belongs with the fw bins re-derivation in QC-FW-FORMS.

## Gates (epyc9, src28m / src28b copies; scripts/gates_s28f.sh)
schema PASS 0 | G0 265 err / 366 warn = s28, 0 new 0 gone | G0C 365 / 541 = s28, 0 new 0 gone | station_lint 3
NONMONOTONE = s28 (sl_sc, not ours) | strict bind (src28b, --strict) rc 0, 0 errors / unbound / undriven, 481 s |
bus_groups 315252676904 = s28 | collector_reattach PASS (no-op), sidecar unchanged.
EQ: every bound .sv byte-identical to the s28 bind (only reset_tree.json / kit_rtl.json provenance and the 6 types'
native_topology plan hash differ) -> 0 data, 0 pin, 0 boot cycles; placement-only.

## route_supply p99 (edge_outline, before -> after)
slw_su_l1__clcc9d0155 1.697 -> 1.695 ring_V | slw_su_l1__cla2a78701 1.697 -> 1.697 | sle_su_l1__cl5ea486db 1.404 -> 1.404 |
sle_su_l0__cl7a55c676 1.203 -> 1.203 | slw_su_l0__cl1e5219ea 1.140 -> 1.141 | slw_su_l0__cl76fb247e 1.143 -> 1.144.
Gap: slw_su_l1 x2 ring_V 1.697 hot at (523.8, 253.8) beside cl_x_su_c_i's W edge (core_V 1.42).  A KIT-CHAN-1 channel
trial on x_su_c_i u_lane6/7 + x_su_c_p1_i u_lane7 (macro gate 0 errors, hops <= 306) only gives 1.698 -> 1.682 (same
spot) -> not adopted; the spot is the ring region at the W edge of the 766-bit cl_x_su_c_i landing macro (529-604 x
180-268), i.e. the lane legs entering that landing -> needs a landing form change there (not a station/position fix);
recommended owner: QC landing lane, after a routed GRT view confirms it (model p99 1.70 is advisory).
Renders: evidence/renders/bands_<type>.png (before | after; red = monitor bands, blue = their status pins).
