# FABLE-CLOSURE-STRATEGY 2026-11-15 19:15 PST: DRT-0255 signature measured, C2 dead, C3b alive; eight levers; stop list

Read-only review by FABLE-CLOSURE-1915. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 17:15 strategy; FABLE-CENSUS-1815; FABLE-PD-S81-1750 / HEAD-NF13 / QC-S4q7ef; rulings r193-r209; queue posts to 19:25;
`failure_breakdown.py` 19:25; KV-ABSPIN-1115 handoff.
Measured by me (19:20-19:40 PST): every wave kit on epyc2/7/8/9/10 + intel1 with a log younger than 30 h (214 types, HBM
excluded): TT setup estimate at the gate, route log class, first `DRT-0255` net, failing access points; the route logs of the
DRT0255-PROOF variants; sign-off JSON and DRC report of one routed col_h9_r2 kit. Scripts: `lanes/fable-closure-1915/`
(scan2.py, agg2.py, aps.py; JSON and log text only, no database opened, no STA run).
MEASURED = read or computed by me. REPORTED = lane post or Fable review. INFERENCE is marked.
Running Fable reviews, not duplicated here: FABLE-PD-S81CORES-1915 (dsdv_bksel_q, dsdv_gunit_l1f_bf) and FABLE-PD-QCHOLD-1915
(QC GRT hold-repair stall, 11 types).

`failure_breakdown.py` 19:25: S81 40/394, HEAD 19/26, QC 6/127, KV 5/56. No change since 15:10.

## 0. What changed since 17:15

1. **DRT-0255 now has a measured signature and the first proof verdicts.** 78 of 92 failing access points (59 kits, first
   two per kit) lie at y mod 4.32 um = 1.89 to 2.70, the M6 PG pair row (pdn.tcl: M6 pitch 4.32, offset 1.968, width 0.288,
   spacing 0.096). Variant C2 (partial cut) FAILED on all three proofs. The die-phase proof p_t49 PASSED its 1st iteration (first
   proof to do so); variant C3b is past the point where C2 failed. Section lever 3.
2. **The class grew.** Latest kit per type: 19 types stop with `DRT-0255` (QC 17, HEAD hd_mesh, S81 leaf t54); 12 of the QC
   17 failed in the last 2.5 h. QC latest routed kits: 17 `DRT-0255`, 5 DRC 0.
3. **S81 col_h9_r2 routes, and its two failures are now separate and both have a fix on the shelf.** Four kits routed today:
   DRC 276-281 (Lef58EolKeepOut dominant, the kit still carries the old `ot_v41_bf_col3_c.lef`), gate setup -143 to -149.
   But routed sign-off TT setup is -267.4 on pv7a260fc0 against -149.5 at its gate: 118 ps lost after the gate (lever 1).
4. S81 measured per-port window on one h9 type: 10-129 ps against the flat 208 (REPORTED, S81-TAPROWS).
5. HEAD MY-tile shorts: cause is two stale closed views, not a mirror bug; refusal form approved (r209). 7 of 7 units with
   more than 200 markers are one MY hd_tile each (REPORTED).
6. hd_serdes private leaf: -261.0 -> -40.6 on GRT RC (REPORTED). Passes by 1.4 ps.
7. TT repair is the default since 18:14 (REPORTED). Order check and M6 check PASS (GENBUG-IMPL 18:06: hold unchanged in both
   scenes, 4 cells added, M6 guide length unchanged). No repaired kit has finished detail route.
8. S81 G3 release list fails `sdc_lint` on 58 types; G3b drops the 59 tables. svc synthesis still stalls (4,792 per-bit
   memory writes). QC S4q7f blocking, S4q7g composed. KV head_eighth pins: 0 free M4/M5 in 623 of 1,351 pin gcells.

## 1. Levers, ranked by types unblocked

| # | dies | lever | unblocks | owner | state 19:40 |
|---|---|---|---|---|---|
| 1 | S81 | col Event F2: per-port window + col3_c pinwire view + IFN 0 + ROM tap rows in one kit; r2 first; explain the 118 ps gate-to-route loss | 216 types | DIE-S81-92, S81-TAPROWS, S81-COLABS-1115 | windows for 1 type; 26 layouts measuring |
| 2 | S81 | G3b: drop 59 tables, per-bit memory write merge for svc, per-port windows for c3x_C / iq_C and the leaf ports | 136 types | DIE-S81-92, GENBUG-IMPL, S81-TAPROWS | G3b composing; svc held |
| 3 | all 4 | `DRT-0255`: C3b form into the gen env when its 1st iteration ends; die phase for face-pin types | 19 types now; every QC hc / sc / stm / su_l1 / st_b / coll kit | DRT0255-PROOF-1115, GENBUG-IMPL | p_t49 PASSED iteration 1 (19:4x); c3b at 50 % of iteration 1 |
| 4 | KV | one-sha tree; raw-branch rows that survive a relay renumber; head_eighth pin windows from the signed ODBs | 51 types | KV-102, KV-ABSPIN-1115, GENBUG-IMPL | v19 binding; ODBs not found on fleet |
| 5 | QC | S4q6d, S4q7e, S4q7g; reset localization on the emitted tree; fw / st_b stations | about 40 held types | DIE-QC-103, QC-CB-GEN-1115 | three binds running |
| 6 | HEAD, all dies | Die route: refuse closed views whose LEF SIZE differs from the outline; re-sign hd_tile 717.12 and hd_st_n4 993.6 | 144 of 326 units; all later die routes | HEAD-MYTILE-1115, HEAD-100 | approved; nf13r kit building |
| 7 | HEAD | hd_serdes: RTL replication beside the private leaf; hd_mesh clock leaf in a pair row; hd_host_e / w on NF12 | 4 types | HEAD-SERDES-1115, HEAD-100 | NF12 kits in placement |
| 8 | S81, QC | cores and hold stall | 2 cores, 11 types | see the two running Fable reviews | running |

### Lever 1. S81 col (216 types)

Evidence (MEASURED): 13 col kits stopped at the gate in the last 3 h: col_h9_r0_p6 -289 to -589 (5 kits), col_h9_r2 -152 to
-231 (4 kits). Four col_h9_r2__clce45cab5 kits passed the -150 triage (-143.0, -145.5, -147.5, -149.5) and routed: DRC 276,
276, 278, 281. pv7a260fc0: DRC report 288 Lef58EolKeepOut, 28 Metal Spacing, 7 cut spacing, 5 Short; `macros/` holds
`ot_v41_bf_col3_c.lef` (old view); sign-off TT setup -267.44, TT hold -4.68 (non-port). REPORTED: col3_c pinwire view
cd64688b278c, one-macro DRC 138 -> 0 (2 instances x 138 = 276); per-port window 10-129 ps on col_h9_r0_p6 pv082a7609, at
least 79 ps back on h9 he; the stale offset table makes gen fail lint (46 errors) unless dropped in the same edit.

Root cause: three independent items. (a) flat 208 ps window on every cross-port pair; (b) col3_c pin wires in OBS
(Lef58EolKeepOut); (c) setup is 118 ps worse after route than at the gate on r2. INFERENCE for (c): the gate reads GRT RC
before the hold repair and before detail route of 276 unresolved markers; not measured which.

Fix:
1. DIE-S81-92: Event F2 as one event: `clock.tap_window.per_port_ps` + drop of the 216 `tap_offset` tables + col3_c view
   cd64688b278c + IFN 0 halves + ROM tap rows. Do not wait for all 26 layouts: bind with the tables that exist, the rest
   take the type value 165 until their table lands (a later delta, SDC only).
2. Pilot = col_h9_r2__clce45cab5 (nearest: -145 at the gate, already routes), then col_h9_r0_p6. Expected on r2: DRC about 0,
   gate about -66 with the window (INFERENCE: -145 + 79), then the TT repair range.
3. S81-TAPROWS: on pv7a260fc0 compare the worst gate path and the worst sign-off path (same endpoint or not; clock or data).
   If the endpoint differs, the gate under-reads r2 and the -150 triage is not a route predictor for col.
4. S81-COLABS-1115: full-kit route with the new LEF is still in GRT (iteration 16 of 30 at 17:27, REPORTED); the F2 pilot
   replaces it as proof if it finishes first.

### Lever 2. S81 non-col (136 types)

Evidence (REPORTED): G3 sound as a plan; slice_station__t8 53, t45 16, serdes__t4 43 lint errors; G3b pre applied the 59
drops with 0 conflicts. svc_hi rs t3 / svc_lo rs t6 stall in yosys canonicalize (PROC_DFF over 45 min) with 4,792 per-bit
write statements in 5 native memories. dsdv_slice_c3x_C__t1 and iq_C__t1 pay the flat 208 on every port; leaf: 1,855 of 4,273
ports without a row. MEASURED: ot_s81sl_leaf__t27 -159.0 at the gate (18:42), leaf t54 `DRT-0255` at y mod 4.32 = 2.61.

Root cause: tool tree inconsistent in itself (lint); memory emitted as one write per bit; windows dropped to flat values.

Fix: DIE-S81-92 adopts G3b with lint 0 on the release list. GENBUG-IMPL: merge per-bit `$mem_v2` write ports into
source-width ports in `bind_native_glue.py` (16 svc types). S81-TAPROWS: c3x_C / iq_C tables next, then leaf. The 46
slice_station and 11 serdes types then launch with the C3b form (lever 3): slice_station is where C3b is proven.

### Lever 3. DRT-0255 (all dies)

Evidence (MEASURED):
- Signature: 59 kits with `DRT-0255` in 30 h; of 92 failing access points 78 (85 %) have y mod 4.32 in 1.89-2.70. Nets: of the
  QC 17, 3 are boundary / feed-through nets, 6 are ring `u_dsel` cells, 8 other internal nets. So it is mostly internal pins
  in pair rows, not face pins.
- C2 (partial cut): c2_t37, c2_fe, c2_hroot all stopped with `DRT-0255` at the start of the 1st iteration. c2_t37 failed
  at y = 136.544 (mod 4.32 = 2.62) and on face pin ft11_i[384] at y = 10.27.
- C3b (100 % gcell-aligned cut M5/M6/M7): c3b_t37 at 30 % of the 1st iteration at 19:37, no error; c2_t37 failed before
  10 %. GRT cost on t37: M6 resource 25.9M -> 23.2M, usage 3.3 %, congestion 0.
- Die phase only: **p_t49 finished the 1st iteration at 19:4x PST with 6,324 violations and no `DRT-0255`; it is in the 2nd
  iteration.** First proof of any variant past the 1st iteration. p_hd_spn at 50 %, no error. p_hd_ctl in iteration 0.
  Update 19:46: c3b_t37 at 50 %, 39,574 violations, no error.
- hd_mesh (new): clock leaf net clknet_leaf_30_clk_t23, access points at y = 304.992 (mod 4.32 = 2.59).

Root cause: unchanged, now measured per access point: pins and guides in the M6 PG pair row.

Fix:
1. DRT0255-PROOF-1115: p_t49 has its verdict (1st iteration passed): post it now and let it run to DRC 0. c3b_t37 reaches
   "Start 2nd optimization iteration" about 20:30 PST (9 min per 10 %); post that line the minute it prints.
2. GENBUG-IMPL: C3b into the gen env of all four dies the same hour; C2 code path removed. First QC kits: slw_hc2 and
   sle_sc_v1 (setup +30 / +7 at the gate, `DRT-0255` is their only failing gate).
3. Check on the first QC hc kit with C3b: GRT overflow. t37 uses 3 % of M6; hc is the congested family. If hc overflows,
   the cut is too expensive there and hc needs rows (S4q7 hc strip), not a smaller cut.
4. If a C3b kit still stops with an access point in the pair row on a cell pin: that is the cell class. Then the keep-out
   form with TAP / fixed cells skipped (the DPL-0033 cause of 15:01), not a return to C2.
5. Face-pin types (hd_ctl, hd_spn, t49, io_cor): die phase (offset 8.448). p_t49 passed; GENBUG-IMPL can put the die-phase
   PDN (without the keep-out flag) into the gen env for the face-pin types now and add hd_spn when p_hd_spn passes.

### Lever 4. KV (51 types)

Evidence (REPORTED): 24 of 24 7u launches failed kit_rtl; tree rebuild started 18:10. Ring split v18 fails the strict bind
with 18 errors: any new hard core renumbers `rst_rl_N`, and the 19 hg / hgi `landing_raw_branches` rows name relays by
number. head_eighth_e2: every signal pin under the blanket OBS M1-M5; free M4 / M5 = 0 in 623 of 1,351 pin gcells, one gcell
inward M2-M5 = 0 in all; one-macro route clean (GRT 0, 0 pin violations); 1.0 um blanket cut lifts M4 / M5 to 8.8 / 11.1
free but models no core metal.

Root cause: pin escape exists only on M6 / M7 above the core edge; rows keyed by a generated index.

Fix:
1. KV-ABSPIN-1115: the signed e0 / e1 / e2 / e5 / e6 databases are not on the fleet; signed records live on AGIdock and
   rtx-pro. Take them from the archive, export exact (-bloat 0), `splice --pin-window-um 1.0`. No blanket cut without them.
2. KV-102 until then: on hg / hgi kits keep parent M6 / M7 trunks off the pin gcell columns (the C3b region form applied
   to pin rows), and read GRT usage at the 623 gcells on the first kit.
3. GENBUG-IMPL with KV-102: raw-branch rows keyed by tap name + xy, resolved to `rst_rl_N` at bind. Removes the v19 / v20
   round trip (2.5 h per hard-core change).
4. From 15:30, unchanged: q2 clock leaves before any hold pad; two pilots to CTS first.

### Lever 5. QC plan events

Evidence (REPORTED): S4q6d, S4q7e ADOPT-OK; S4q7f 24 of 24 columns fail, S4q7g = +3 on 48 + 24 sinks. sc reset hops
690-1,041 um stay open: bind published the plan collector tree, 77 of 126 types differ from the emitted tree; fix READY
(bind-reset-tree-1115). MEASURED: slw_fw_v2 -438.7, sle_st_b_v2 -186.7 / -201.7 still the latest kits (25-28 h old);
cbf_q01_s2 -884 at the gate on the old S4Q2 plan (attempt 12, 0.6 h ago).

Fix: DIE-QC-103 adopts S4q6d then S4q7e; cb pilot = cbn_q11 only, read at kit GRT. After bind-reset-tree merges, re-derive
the sc reset rows (dry-run on 9 of 9 types before posting). First fw and st_b kit on S4q7: gate against -439 and -202. Stop
relaunching cb types on S4Q2 / S4Q3C: -884 is a station class, no kit setting reaches it.

### Lever 6. Die route: closed views

Evidence (REPORTED): hd_tile view 708.48 against outline 717.12 (566 E-face pins 8.64 um short in 264 instances); hd_st_n4
1,123.2 against 993.6 (128,770 um2 over lep0N). All 7 units with 218-262 markers sit in one MY hd_tile each; R0 tile units
are at 0. Other 13 HEAD type views and 13 core views: 0 mismatches. 37 of 326 units launched on the stale kit.

Fix: HEAD-MYTILE-1115 refusal merged; HEAD-100 re-signs both types at the plan outline; rerun the 144 MY units on nf13r.
New Sonnet lane or DIE-ROUTE-ABS-1: the same SIZE-against-outline table for S81, QC, KV closed views before their first
die-route unit (REPORTED 0 mismatches there for plan abstracts only; closed views not scanned). u018 (1 M4 spacing, 54 GB):
stop at step 3 when the count is flat.

### Lever 7. HEAD types

Evidence: REPORTED hd_serdes private leaf -40.58 (gate -42), same form at the macro leaf -46.68, tap group -69.1.
MEASURED: hd_mesh attempt 4 gate -51.0 then `DRT-0255` on a clock leaf.

Fix: HEAD-SERDES-1115: 1.4 ps of margin on GRT RC is not a closed type (col_h9_r2 lost 118 ps between gate and sign-off,
hd_host_e lost 54 ps from CTS to GRT). Keep the private leaf row in NF13 and replicate the `ldr` registers in RTL in
parallel; READY only on routed sign-off. hd_mesh: relaunch only with C3b (lever 3); its -51 is TT repair range.
hd_host_e / hd_host_w: read the NF12 gate; no new action.

### Lever 8. Cores and hold

dsdv_bksel_q (-257, FF corner on a TT lib), dsdv_gunit_l1f_bf (hold -42, ECO rewires clock nets): FABLE-PD-S81CORES-1915.
QC hold stall: FABLE-PD-QCHOLD-1915. MEASURED here only: FF hold estimate at the gate of the fresh QC kits that reached
route is -2 to -108 (sle_stm_v2 -106.6, slw_stm_v3 -107.7), on the stm family the hold review covers.

## 2. Stop list (technical dead ends)

1. Variant C2 (partial PG-row cut): 3 of 3 proofs failed. `OT_PG_CELL_KEEPOUT` in its 15:01 form (DPL-0033).
2. Unchanged relaunch of the 19 `DRT-0255` types; QC hc / sc / stm / su_l1 / st_b / coll kits without C3b (12 failed in 2.5 h).
3. col kits on the current tree: 13 more gate stops and 4 routed-not-signed in 3 h add no information.
4. Reading -150 at the gate as "will sign off after repair" on col (118 ps gap on r2).
5. hd_serdes READY at -40.6 on GRT RC; plan tap group for the three `done[0]` flops (-69.1).
6. place_lines / windows-mirror forms for MY tiles; outline growth for hd_st_n4; more units on the stale kit.
7. Pinwire on KV detail views (one cluster touches thousands of pins); blanket cut without the signed ODB.
8. S4q7f as bound; row-0 pads for the row-2 shift; cb relaunches on S4Q2.
9. Widening or bypassing `sdc_lint`; repairing c3x_C / iq_C against the 208 window; a fourth post-route hold ECO on gunit.
10. Kept from 17:15: TT repair as cure below -150; `MAX_ROUTING_LAYER = M7`; density / `band_spread` for `DRT-0255`; band
    moves for the 401-403 um hops; a third post-route hold pass on one kit.

## 3. Not checked

- Only p_t49 has finished its 1st iteration (no DRC 0 yet); C3b has no final verdict. Where the baseline t49 and hd_spn kits
  failed inside the 1st iteration was not read, so "past the failure point" is measured for c3b_t37 only.
- The pair-row share uses y only; x against the M7 pair (pitch 8.64) was not tested. Layer of each access point not decoded.
- Which kits carry `OT_TT_SETUP_REPAIR`: the key is not in `config.mk`; no repaired wave kit result was identified.
- The 118 ps gate-to-route gap is one kit (pv7a260fc0); the other three routed r2 kits were not opened.
- KV archive presence of the signed e* databases; closed-view SIZE table for S81 / QC / KV.
- G3b, S4q6d / S4q7e / S4q7g, 7u_c1 and NF13a kit results: none exists yet.
