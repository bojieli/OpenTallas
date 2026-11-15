# FABLE-TYPES-QC-EAST 2026-11-14: root causes for the unclosed QC east types

Scope: qwen_compute types sle_, cbn_, cbx_, cbf_, coll_ and the other non-slw types (glue, native59, tt_ctlm). 79 unclosed rows; 50 have a physical-design result on record (list in section 9). Read-and-diagnose only: 99 wave job logs of the last 3 days, kit logs of 493 kit dirs on 7 hosts (config.mk, pregrt_ff_hold.log, hold_gate.log, 5_1_grt.log, 5_2_route.log, congestion.rpt, 4_cts_final.rpt), the QC wave source (epyc9 `wt/qc-s29-tree2`) against hub main. No job started, nothing shared changed. Log times in kit dirs are UTC.

Status words: MEASURED = read from a log, report or source file; INFERENCE = fits the numbers, not proven.

Not redone here (already reviewed today, reused): coll_n, su_l0 pin-over-PG, repair4_leaf (FABLE-HARD-QCHEAD); DRT-0255 class, cbn tile faces, memory kills (FABLE-WAVE-REVIEW).

## 0. Verdict

Two flow faults, not design faults, explain every "HOLD_STRUCTURAL NEEDS_RTL" end in this group and most of the cell growth of the station types. Both are new findings and both have a same-family A/B in today's logs.

| # | cause | types | status | owner |
|---|---|---|---|---|
| A | the pre-GRT hold repair does its job, then its accept test throws the result away; GRT then repairs the whole debt at 13-17 s per buffer and the 3-h guard calls it structural | stm_v1, fw_v1, sc_v1, st_b_v1 split, hc0, fe_v3, cbn_q11 (7 now; st_a x3 on 11-12 likely) | MEASURED, 3 A/B pairs | NEARMISS-ECO (flow), cc DIE-QC-103 |
| B | QC wave source carries the old relay_bay.py: FF hold picks a kit-wide repeater pitch of 33-75 um; +117 k to +275 k repeaters per kit (+31 to +68 %) | stm x5, fw x5, fe_v1 x2 (12) | MEASURED; fix is on main (R-FLOW-3), not in the QC source | DIE-QC-103 (source), OVERSIZE-1 (re-measure) |
| C | cbn / cbx / cbf: tile pin faces and the tile output pipeline; three blockers stacked (GRT overflow 90 k, TT setup -775 ps, cross-tap hold -112 to -237 ps on 7-30 k endpoints) | cbn x7, cbx x3, cbf x2 (12) | overflow and path MEASURED; common cause INFERENCE | DIE-QC-103, TYPE-QCCOLLN |
| D | DRT-0255 in M6 PG pair rows | 12 types | class MEASURED before; one more case measured here | PG-AWARE-1 (in flight) |
| E | DRT-0206 off-track strap pins | fe_v1, fw_v1, fw_v2, sc_v3 (4) | MEASURED before; snap applied to 141 dirs, no proof build yet | TYPE-QCCOLLN |
| F | routed near misses | su_l0 x2, coll_ft x2, coll_ftc (5) | MEASURED | NEARMISS-ECO |
| G | su_c: hard-core clock pin without access point | su_c (1) | MEASURED | DIE-QC-103 (core view) |

Memory kills (make Error 241) ended 12 more builds of this group today (cbf_q00, cbn_q01, cbn_q11, fe_v1 x2, fe_v3, sc_v1, sc_v3, fw_v2, stm_v1, coll_ftc; hc0 and hc2 as the wrapper form, exit 6). That is fleet fix 3 of the wave review, not repeated here; B removes part of it.

## 1. Cause A: the pre-GRT hold repair result is discarded (MEASURED)

What the kit does: after CTS, `pregrt_ff_hold.tcl` repairs FF hold on placement parasitics in two passes (all paths to +5 ps; cross-tap pairs to the 45-ps guard), then writes `4_cts.odb` only if an accept test passes. The test (hub main `tools/die_plan/pregrt_ff_hold.py` lines 250-251, same text in the kits):

```
if {$pg_s1 < [expr {min($pg_s0, 0.0) - 1.0}]} { set pg_fail "TT setup loss ..."
} elseif {$pg_w1 < $pg_w0 + 1.0 && $pg_n0 > 0} { set pg_fail "no hold gain ..." }
```

Both arms compare one number, the worst slack over all paths.
- Hold arm: the worst hold path of these kits is a port-input path (class `port_in`, -84 to -123 ps, 474-4,102 endpoints: the forwarded ring inputs at the -85 ps input contract). The repair cannot move it. If that one endpoint does not gain 1 ps, everything else is thrown away.
- Setup arm: the TT setup figure here is the placement estimate, already -305 to -515 ps on these kits (the same path reads -7 ps after GRT on st_b_v1: TL-QCSTBV1 12:52). A loss of 1.1 ps on that estimate vetoes the build.

Port hold is the parent's under R-MINIMAL (sign-off scores "core-owned only"), so the veto comes from a path that is not a gate.

| kit | classes before (endpoints @ worst ps) | pre-GRT result | GRT hold repair | end |
|---|---|---|---|---|
| sle_stm_v1 cl27746664 (epyc9 s29q103S a6) | port_in 4,102 @ -111, cross_tap 1,254 @ -76, same_tap 98 @ -18, port_out 7,023 @ -70 | cross-tap pass reached +5.0 ps, 0 endpoints, +30,156 cells; FALLBACK "no hold gain -110.69 -> -110.69" | starts -85.2 ps, 5,838 endpoints; 1,701 buffers in 24,811 s; -18.9 ps, 4,229 left | OT_HOLD_STALL NEEDS_RTL |
| sle_stm_v1 clbe630b9c (epyc7 a6), same family | port_in 4,102 @ -123, cross_tap 494, port_out 9,065 | accepted, +24,574 cells | starts -18.6 ps, 33 endpoints; closed in 517 s | went on to route |
| sle_fw_v1 cl9d029624 (intel1 a7, epyc8 a8; identical twice) | port_in 3,398 @ -110, cross_tap 46, port_out 8,089 @ -64 | FALLBACK "TT setup loss -305.49 -> -306.61" | starts -59.3 ps, 6,875 endpoints; 1,328 buffers in 22,508 s / 17,345 s; -41.3 ps, 6,198 left | OT_HOLD_STALL NEEDS_RTL, twice |
| sle_fw_v1 clf58b4dfb (epyc10 a7), same family | port_in 3,398 @ -101, cross_tap 146, port_out 8,968 | accepted, +27,297 cells | starts -24.7 ps, 3 endpoints; closed in 70 s | went on to route |
| sle_sc_v1 cl7479a5ec (intel1 a3) | port_in 2,803, cross_tap 2,133 @ -93, port_out 6,932 | FALLBACK "no hold gain -107.56" | starts -98.2 ps, 8,375 endpoints | killed in GRT (Error 241) |
| sle_hc0 cl05696ed1 (epyc8/10 a6) | port_in 1,576, cross_tap 633, port_out 2,484 | FALLBACK "TT setup loss -515.45 -> -518.27" | not reached yet | will repeat the pattern |
| sle_fe_v3 (intel1 s29q103S2 a7) | port_in 3,297 @ -118, port_out 1,458 | FALLBACK "no hold gain" | killed in GRT (Error 241) | |
| cbn_q11 cl5cc92dfe (epyc10 a8) | cross_tap 15,194 @ -214 | FALLBACK "tool error" | GRT-0116 | see C |

So: with the pre-GRT result kept, the GRT step finds 3-73 endpoints and closes in 1-9 minutes on every kit of the group (15 kits in the scan). With it discarded, the same family shows 5,838-8,375 endpoints and needs 6-7 h for one chunk. The stall line then ends the build as HOLD_STRUCTURAL (`failfast_rules.py`), and the wave does not retry it. None of these four types has a structural hold problem: their internal classes are 50-2,100 endpoints and close in one pass.

Why the GRT step is that slow: 14.6 s per buffer on stm_v1 (680 k instances after B), 4.2 s per buffer on fe_v3 (189 k). Cost grows with the netlist; B makes it worse.

sle_st_b_v1 pvc5a85fd4__pv38472fb8 (intel2, stall at -21.6 ps on 5,144 endpoints) and the three st_a stalls of 11-12 (-91 to -101 ps on 10-16 k endpoints) show the same stall signature; their kit dirs are gone, so for these the cause is INFERENCE.

Dead ends
- "NEEDS_RTL, not retried" for these types (TL-QCSTBV1 19:25 for the st_b split; OVERSIZE-1 lists stm_v1 as "hold-structural fail"). No RTL or plan change is indicated by the numbers.
- Raising the 3-h cap or the buffer cap: the repair would take 15-25 h per kit.
- A late ECO on 4,000-6,000 endpoints.

Fix (flow logic, `tools/die_plan/pregrt_ff_hold.py`)
1. Hold arm: judge the gain on what the repair can move: the count (or TNS) of violating endpoints outside `port_in`. Accept when it falls; the `port_in` residue is printed as today and stays the parent's.
2. Setup arm: apply the 1-ps loss test only while the estimate is at or above the gate (-42 ps). Below it the figure is a placement estimate that the route replaces; allow the loss and print it.
3. `hold_guard_grt.tcl`: a chunk that gained WNS and cut TNS by more than half is not a stall. Print the 3-h stop as OT_HOLD_BUDGET (continue to route, residue to the late ECO), keep NEEDS_RTL for the no-gain window only. This matches the file's own header ("the residue goes to route / sign-off / post-route hold ECO").

Proof in one build: sle_fw_v1 cl9d029624, resume from `3_place.odb` + CTS on intel1 `.../s29q102B0/items/sle_fw_v1__cl9d029624/attempt_7` with the patched tcl. Pass = "OT_PREGRT_FF_HOLD after" line instead of FALLBACK, and "OT_HOLD_GUARD_GRT start" at or under 100 endpoints (sibling: 3). Then relaunch stm_v1 cl27746664, sc_v1 cl7479a5ec, hc0 cl05696ed1, fe_v3, st_b_v1 pv38472fb8.

## 2. Cause B: hold-picked repeater pitch on every net of the station kits (MEASURED)

- `OT_MAXWIRE_UM` in the kits: stm_v1 / v2 / v3 = 33; fw_v3 = 40; fw_v1, fe_v1 = 62; fw_v2 = 75; every other QC kit = 120 (the die default in kit_wave.json).
- Source: the kit's `relay_bay.py` picks the largest BUFx4 pitch whose hop meets setup, slew and a +10 % FF hold margin, and writes it into the kit-wide limit. stm_v1 table: lane cws1 passes at 75 um, x_fe_fw at 40, the worst lane sets 33.
- RULEBOOK R-FLOW-3 (11-13) already removed this: "FF hold no longer picks the repeater pitch"; hub main `relay_bay.py` has it (lines 18-24, 242). The QC wave source `epyc9:/srv/opentallas-scratch2/claude/wt/qc-s29-tree2` (HEAD 1e3b302be8) has the old file: 0 matches for HOLD-MARGIN. Kits of the newest events (s29q103S3M2) still show 62 / 75 / 40.

| kit | pitch | instances before -> after the post-GRT repair | added |
|---|---|---|---|
| sle_stm_v1 cl27746664 | 33 | 404,570 -> 680,238 (275,668 buffers on 91,694 nets) | +68 % |
| sle_stm_v1 clbe630b9c | 33 | 426,379 -> 699,061 | +64 % |
| sle_stm_v2 cl55be2264 | 33 | 424,580 -> 696,183 | +64 % |
| sle_stm_v3 | 33 | 357,473 -> 582,590 | +63 % |
| sle_fw_v1 cl9d029624 / clf58b4dfb | 62 | 375,684 -> 530,874 / 406,394 -> 560,703 | +41 / +38 % |
| sle_fe_v1 cl1cbb7497 | 62 | 396,656 -> 526,907 | +33 % |
| sle_fw_v2 cl6740750e / cl69f5e854 | 75 | 379,414 -> 496,887 / 380,753 -> 498,376 | +31 % |
| for comparison, 120 um: st_b_v1, hc0, hc2, su_l0, sc_v1, coll_ftc | 120 | +1 to +9 % | |

(Instance counts include about 94 k tap and endcap cells per kit.) The kit's own census predicted it: stm_v1 "maxwire_est 259,075, projected_nontap 570,035, cap 400,000, WARN OVER_CAP".

Consequences seen in the same kits: GRT 3-10 h, the 14.6 s per hold buffer of cause A, DRT memory kills (stm_v1 clbe630b9c, fw_v2, sc_v3 died in detail route with Error 241), and the OVERSIZE-1 inventory row "slw_fw_v1 215.5 k, GRT census 418-428 k, 61-64 %", which counts these repeaters, not logic.

Dead end: splitting stm / fw / fe types for size before this is fixed. stm_v1 is 311 k non-tap cells at CTS; the other 260 k are repeaters at 33 um.

Fix: bring `relay_bay.py` (and its R-FLOW-3 table verdict) from hub main into the QC wave source as a flow-only change, re-generate the 12 kits. This is the concrete case for wave-review fix 5 (lift the freeze for flow-only source). The rulebook measured the effect on S81 t21: 27,226 -> 8,668 repeaters, 0 slew pins, hop hold unchanged (2,207 against 2,243 hold cells).

Proof in one build: sle_stm_v1 cl27746664 re-generated; pass = `export OT_MAXWIRE_UM = 120` in config.mk, the "OT_MAXWIRE leaf instances" line under +10 %, sign-off slew 0 pins. If slew pins appear, lower the die value to 100, not the hold-picked pitch (rulebook text). Run it together with the cause A proof: stm_v1 needs both.

## 3. Cause C: cbn / cbx / cbf

MEASURED
- Geometry (cbn_q00 cl622f65d2, epyc8 s29q103S a7): outline 1235.52 x 2566.08; four hard tiles 457.92 x 1157.76 at x 103.68 and 691.2: t00 R0, t10 R0 (lower row), t01 MY, t11 MY (upper row); centre channel 129.6 um.
- GRT: total overflow 90,044 = M6 79,067 + M8 10,886 at M6 use 3.55 %, M8 0.73 %. The congestion report lists 10,069 gcells: 4,857 over t00, 5,212 over t11, none over t10 or t01, none in a channel; 9,998 have capacity 0; 99 % horizontal. Named nets: `u_bound.pq_u_t_1_1_n_b[*]` (2,808 entries), the rest anonymous repair nets. Same picture as the wave review found on another cbn kit; GRT-0116 on 5 cbn and 3 cbx kits (11-10 to 11-14).
- Setup at CTS: WNS -775 ps, 2,046 endpoints, TNS -431 ns. Worst path: `u_bound.u_d3_u_t_1_1_t_out.r[0][276]` -> `r[1][276]`, two stages of the tile-output pipeline with no logic between them, data arrival 1,622 ps. Pre-route TT estimates on the family: cbn -821 to -923, cbx -916, cbf_q00 -542.
- Hold at CTS: cross-tap class 7,391-30,145 endpoints at -112 to -237 ps (cbf_q00 12,706 @ -193, cbx 17,817-19,743 @ -227 to -232). The pre-GRT repair spends 26-61 k cells and still leaves -175 ps on 1,099 (cbn_q11 cl49ae4555), -205 on 2,079 (cbx cl94a12200), -86 on 324 (cbf_q00 cl1b5a6458).

INFERENCE: one cause for the first two. t00 and t11 turn their pin face to the outer margin; their buses reach the glue by crossing the tile itself (capacity 0) or by going around it, and the output pipeline stages sit at the two ends of that detour, which is the 1.6-ns stage. I did not trace where each bus is consumed.

So a cbn that passes GRT with allow-congestion still fails setup by about 700 ps, and after that carries a cross-tap hold debt above the 10 % cell budget of R-FLOW-5. Three blockers; the wave only ever shows the first.

Dead ends
- Unchanged cbn / cbx relaunches (attempt numbers 7-30) and allow-congestion alone.
- Dropping the mirror without a replacement (DIE-QC-103 19:20 "cbn mirror stays dropped"). The measurement says t00 and t11 need an event.

Fix
1. Plan event: t00 and t11 turned so all four tiles face the centre channel (mirror keeps the signed core), or pins re-exported by consumer side. TYPE-QCCOLLN's as-is against mirror place-only what-if on epyc2 is the right test; judge it on three numbers, not on overflow alone: gcells with capacity 0 crossed, arrival of the `u_d3_*_t_out` stage, cross-tap endpoints.
2. Generator: spread the `u_d3_*` pipeline stages along the tile-to-glue route (anchor r[0] at the tile pin, r[1] at the consumer side, r[2] between) instead of leaving them to global placement. This holds whichever way the tiles face.
3. Cross-tap hold: 133 tap ports with an 80-100 ps window plus the 45-ps guard make 10-30 k pairs. That is R-CLOCK's tap plan for the tile type (fewer taps, or pairs kept on one tap); list the pairs from `pregrt_ff_hold_open.tsv` of cbx cl94a12200 (epyc7 a7) before choosing.

Proof in one build: cbn_q00 cld7bf7197 with the mirrored plan to GRT: overflow under 1,000, CTS setup above -100 ps on the d3 stage.

## 4. Cause D: DRT-0255 in M6 PG pair rows (class owned by PG-AWARE-1)

Types of this group, today: fe_v3 (`x_st_b_i[4]`, `x_fw_ctl_p2_o[530]` at x 198.4), fw_v2 cl69f5e854 (`hr_ei[227]` at x 14.8-26.8, y 485.6), hc0 cl4baa7c9c (ring `u_cland_x_hc1_st_a_i ... dch[3]`), hc2 clf60c5152 (`b_hw_i[136]`), st_b_v2 clfde1249e (`x_fw_ctl_p2_i[464]`) and both pv splits (ring `u_cland_b_hw_ctl_hc3_i ... dch[15]`, `dch[21]`), stm_v2 cl55be2264, stm_v3, su_l1 clc6d66f5b (`u_ft_rsn_o_1`, `_3`), coll_ucie (`net309`, same box on two hosts), coll_n. All had OT_PG_TRACK_TRUTH off (old source).

One more case measured: hc2 `b_hw_i[136]`. The port pin is at x 47.008 on the south edge; the failing boxes are 15-35 um away at y 22.8-26.8. Access points in the log: (74.670, 23.328) and (80.379, 23.643 / 23.679). The M6 PG pair there is y 23.568-24.240 (offset 1.968 + core 4.32, pitch 4.32, width 0.288, spacing 0.096). The cell pin is under the pair; the other point is 240 nm below it. So a failure named after a port is still the pair-row case, not a pin-on-stripe case.

No new fix: PG-AWARE-1 (die phase + cell keep-out + PG-track truth). Its proof list should include one ring-net case from this group (st_b_v2 pv41c959f3) since three of the twelve are landing-ring nets that CLAND-MACRO-1 would remove instead. Do not relaunch the twelve unchanged.

## 5. Cause E: DRT-0206 strap pins

fe_v1 cl1cbb7497, fw_v1 clf58b4dfb, fw_v2 cl6740750e, sc_v3: detail route ends in checkConnectivity. Known (off-track strap pins); TYPE-QCCOLLN snapped 141 kit dirs in place and the generator patch is on main. Open: no build has yet shown DRT-0206 gone. fw_v1 clf58b4dfb is the proof (its hold and GRT are clean: 3 endpoints, GRT done). With B it also drops 150 k repeaters.

## 6. Cause F: routed near misses (NEARMISS-ECO)

| build | DRC | TT setup | FF hold | state |
|---|---|---|---|---|
| coll_ft cla4a25d77 (s29q103S a9) | 0 | +19.4 | -6.9 on 198 -> +3.97 after ECO | ECO PASS 14:30 (KIT-OPS-4); needs ingest and archive, then it counts |
| coll_ft cl78c7b300 (a5) | 0 | +13.3 | +0.9 | only the parent IO receipt and TT slew open; ECO launched 19:10 |
| su_l0 cl086d85ba (a6) | 3 | +4.8 | -13.3 on 15 | ECO running; DRC 3 = pin over PG pair (FABLE-HARD-QCHEAD 2) |
| su_l0 cl7a55c676 (a5) | 3 | -19.0 | -45.3 on 40 | same |
| coll_ftc (11-11 a?) | 0 | -90.9 | -16.5 on 38 core-owned | not a near miss on setup; 11-14 rebuild estimates -39 pre-route, died in detail route (Error 241 at 8,941 violations, 10 %) |

coll_ftc: resume the 11-14 build at detail route from its `5_1_grt.odb` (intel1 s29q102B0 a5, GRT hold closed with 1 buffer). No design change is indicated until it routes.

su_l0 / su_l1 advisory: the cross-tap class is 6,314-12,069 endpoints at -107 to -172 ps and the pre-GRT repair adds 23-40 k cells (12-20 % of the kit; R-FLOW-5 calls more than 10 % a structural hold class). They route and nearly sign off, so this is layout cost, not a blocker.

## 7. Cause G: sle_su_c

epyc10 s29q102B0 a6: `[ERROR DRT-0073] No access point for u_bound.u_u_suvm_u_vm8q_u_va/ck (qfd_dv_s8x_vmr)`. The clock pin of that hard core has no legal access in this placement; the wave review saw the same class on S81 (fix the core view once: pin shape or the blockage over it). Hold is no longer the blocker here: -410 ps on 11-12, now cross-tap -180 on 4,832, repaired to +5 ps with 25,073 cells. Pre-route TT estimate -702 ps is open and unmeasured after route.
Proof: check the `ck` pin of the qfd_dv_s8x_vmr LEF against the parent M6 / M7 PG at its site (the scan `pinscan.py` of FABLE-HARD-QCHEAD does this), fix the view, resume su_c at detail route.

## 8. What to do, in order

1. A + B together (flow only, no plan change): patch the accept test, bring R-FLOW-3 relay_bay.py into the QC source, re-generate stm / fw / fe; proof builds fw_v1 cl9d029624 and stm_v1 cl27746664. Unblocks 12-14 types and takes about 2 M instances off the fleet.
2. C: wait for the mirror what-if, read the three numbers, then one cbn plan event with the pipeline anchors. 12 types.
3. D, E: no relaunch before PG-AWARE-1 lands; fw_v1 clf58b4dfb is the DRT-0206 proof.
4. F: ingest coll_ft cla4a25d77 now; resume coll_ftc at detail route.
5. G: su_c core view.

## 9. Types reviewed (50)

stm_v1 cl27746664, clbe630b9c; stm_v2 cl55be2264, cl7b3062fa; stm_v3; fw_v1 cl9d029624, clf58b4dfb; fw_v2 cl6740750e, cl69f5e854; fw_v3; fe_v1 cl1cbb7497, cl8210183c; fe_v3; sc_v1 cl7479a5ec; sc_v3; st_a_v1 cl67389ecd, cl989804f6__cled3c1d7b; st_a_v2; st_b_v1 pv0e7b1dcc, pv38472fb8; st_b_v2 clfde1249e, pv41c959f3, pvcd986c42; hc0 cl05696ed1, cl38badc56, cl4baa7c9c; hc2 cl3edce1b8, clf60c5152; su_l0 cl086d85ba, cl7a55c676; su_l1 clc6d66f5b; su_c; cbn_q00 cl622f65d2, cld7bf7197, cldbcda913; cbn_q01 cld9ff4c40, cldd6ea846; cbn_q11 cl49ae4555, cl5cc92dfe; cbx_q10 cl89936551, cl94a12200, cl94a12200_h; cbf_q00 cl1b5a6458; cbf_q01; coll_n; coll_ucie; coll_ftc; coll_ft cl78c7b300, cla4a25d77; coll_s.

No physical result on record (flow or waiting only): sle_ctl x6, fe_v2, fw_v3 newest kits, hc1 x2, hc2 clcc5e3e61 (pre-GRT accepted, in flight), sc_v2, su_l1 cl5ea486db, cbf s2 forms, coll_core, glue, native59, tt_ctlm.

## 10. Evidence and limits

- Tables: rtx-pro `/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/qe_tab.txt` (per-kit hold classes, max-wire growth, GRT hold, errors), `qc_jobs.txt` (job ends), scripts `qe_scan.sh`, `qe_tab.py`, `cbn_cong.py`.
- Not done: no proof build of the A patch (the A/B pairs are existing builds of sibling types, not the same netlist); no trace of the cbn bus consumers; no check of the su_c pin geometry; the st_a and st_b-split stalls are attributed by signature only.
