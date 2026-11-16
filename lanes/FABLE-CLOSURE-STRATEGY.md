# FABLE-CLOSURE-STRATEGY 2026-11-16 01:30 PST: S81 landing rings are placed whole in netlist order (the only die that does); seven levers; stop list

Read-only review by FABLE-CLOSURE-0130. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 23:15 strategy; FABLE-FIX-S81-COL-SPECS, FABLE-PD-S81-F2r, FABLE-PD-QC-S4q8, FABLE-FLOW-0015; handoffs DIE-S81-92,
FABLE-FIX-S81-COL / HEAD-TYPES / QC-HCFE, KV-102; posts to 01:17; rulings r256-r266; `failure_breakdown.py` 01:11.
FABLE-PD-S81-0117 had not landed at 01:25; lever 1 is input for it.
MEASURED = read or computed by me 01:10-01:30 (text, JSON, logs and congestion reports; no database opened, no STA run).
REPORTED = lane post, Fable review or COORD. INFERENCE is marked.

`failure_breakdown.py` 01:11: S81 41/394 types (62/64 cores), HEAD 19/26, QC 7/127, KV 5/56. Its classes are kit-row states,
not technical classes; the technical content below comes from the kits and plans.

## 0. Verdict

1. **The S81 leaf GRT failures are not caused by the B6gE band rectangles.** They are caused by how the ring is placed
   inside the band. S81 is the only die whose plan has no `ring_place` key on any landing band (0 of 1,255), so every
   ring is packed FIRM, whole (flops and logic), in netlist order. HEAD, QC and KV use `ring_place: "ff"` on every wide
   ring. Restoring the B6gsl band rectangles (F2s G4 `BAND_RESTORE_TYPES`) does not address this and should not be the
   gate for the y-slot rows.
2. The converged S81 / QC / HEAD trees now carry die phase, TT repair, C3b and the RC table. The S81 tree was cut one
   merge before the col clock keys, so those keys would again have no reader.
3. hd_st_k5 is a missing face register (confirmed independently of the lane). hd_serdes fails in the recovered-clock
   group, which the TT repair does not report.

## 1. What moved since 23:15

| 23:15 lever | state 01:25 |
|---|---|
| 1 trees that read the keys | Built from main e594a73db75: `kw45/src_{qc,s81,head}_pin_e594a73db756` (epyc10). MEASURED in each `gen_phys.py`: OT_TT_SETUP_REPAIR 12, OT_PG_DIE_PHASE 3, OT_PGCAP 17, OT_RC_SIGNAL 6 occurrences. QC published read-only, replicating. S81 and HEAD not switched yet. Gap: `core_pin_lead` 0 occurrences (section 2 lever 2). |
| 2 signal RC | Merged as a table (r258): S81 x1.00, QC x1.25, cores x1.10. Validation inside 20 optimistic / 40 pessimistic on col, hc2, fe_v1, b1p (REPORTED). `repair_design` is on in the TT repair. Open: HEAD and KV have no entry; the core flow is not wired. |
| 3 S81 col | Four-part clock form proven at CTS: 1,476 -> 144 failing endpoints. Tool part READY and approved (r266). New first blocker: the flat 165 ps window. Spec 0b (measured per-port windows) READY at b82b6c5dc1d. |
| 4 QC hc | P0 (E1 repair through route) in route, no sign-off number. P2 (leaf placement groups) stopped in detailed placement, cause not read. P1 waits for the QC tree switch. |
| 5 KV | Four ectlk cores signed. 7yh composed, gate running. pv ring plan r3n: 209 hard ring cores, 211-258k cells per type by plan estimate; bind not passed (R8_STALE). |
| 6 HEAD | he3 -10.5, hw3 -9.7, n3t +77 at the gate, all in route. k5 root cause found (lever 4). sd2 -127.85. |
| 7 serdes / phy / glue | S81-SERDES-PHY-1116 started (private main-based proof). svc memory: proposal posted, waits for a go (lever 7). |

## 2. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner | status |
|---|---|---|---|---|---|
| 1 | S81 | Landing rings: flop-only bit-ordered placement (`ring_place: "ff"`), bands grown in depth | 93 types with a ring >= 1024 bits (174 with >= 512); all 13 y-slot kits | DIE-S81-92 (rows), new Sonnet lane S81-RING-FF (proof kits), S81-CA-BAND (composer) | **NEW root cause** |
| 2 | S81, QC, HEAD | Switch to the converged trees; rebuild S81 once more with the col clock branch | S81 387, QC 120, HEAD 7 | TOOLS-CONVERGE-1115, KIT-OPS-5 | built, one gap |
| 3 | S81 | col: clock form rows, then measured per-port windows, then the 26 remaining endpoints | 216 types | S81-COL-CLK-IMPL, FABLE-FIX-S81-COL, DIE-S81-92 | owned, direction right |
| 4 | HEAD | Face register on the falling-edge rings of hd_st_k5 and hd_st_turn; hd_serdes recovered-clock cone | 2 + 1 types, plus he3 / hw3 / n3t in route | FABLE-FIX-HEAD-TYPES, HEAD-100 | owned; serdes part new |
| 5 | QC | hc leaf: calibrated repair, then leaf placement; die phase + C3b for the 9 placed `DRT-0255` types | 16 hc + 9 | FABLE-FIX-QC-HCFE, DIE-QC-103 | owned, waits on lever 2 |
| 6 | KV | pv ring child cores, hg v25h; `ring_place` on the two hub types | 13 pv + 21 hg; hub_C, hub_Wo | FABLE-FIX-KV-PV, KV-102 | owned; hub part new |
| 7 | all | RC table for HEAD and for the core flow; S81 svc staging memory as a macro | HEAD gate reads; bksel; 16 svc types | GENBUG-IMPL | partly owned |

### Lever 1. S81 landing rings: the placement form, not the band rectangle

Evidence (MEASURED).

Overflow location, y-slot kits of S81-LEAF-PLAN at `congestion-15.rpt` (epyc9, `evg/kit/ys_*`):

| kit | band rects of the two 1152-bit rings | overflow total | inside the two bands | within 40 um of them | other bands |
|---|---|---|---|---|---|
| t65 | ft0_i 38.9 x 438.5 (y 17-456); ft1_i 69.1 x 224.6 (y 458-683) | 231,401 | 102,768 | 81,007 | 1 |
| t1 | ft0_i 71.3 x 240.0 (y 17-257); ft1_i 71.3 x 240.0 (y 247-487) | 249,877 | 182,298 | 63,249 | 0 |

- On t1 both bands are 71 um deep and sit on their own pin window (pins y 6-246 and 248-487). It fails as hard as t65.
  Inside the bands H and V overflow are equal (ft0_i 54,523 H / 54,959 V), which is internal ring wiring, not a bus
  crossing.
- The six 128-bit rings and the monitor ring of t65 have 1 overflow gcell in total.
- The two kits that reached GRT 0 (strip t10, t74) have no ring of 256 bits or more. t14 form R (GRT 0 after 14 extra
  iterations) has rings of 320 and 704 bits. Every failing kit has 1152-bit rings. Ring width separates pass from fail;
  band shape does not.
- Place log of t65: `OT_CLAND placed 68983 actual mapped cells FIRM in nonoverlapping reserved bands`; t1: 71,706. The
  band tags in `landing_placement.tcl` are plain `ring:ft0_i`. No `OT_CLAND pinslot` line is printed although
  `OT_CLAND_PINSLOT = 1` is in `config.mk`: the pin-slot branch needs a `+ff` tag, so the key does nothing here.
- Plan census of `clock.landing_contract.bands[*].ring_place`:

| die (plan of record) | bands with `ff` | bands without | wide rings (>= 512) without `ff` |
|---|---|---|---|
| S81 B6gG3b (t65 band rects are equal in B6gE) | 0 | 1,255 | 459 bands in 174 types |
| HEAD NF13a | 67 | 0 | 0 |
| QC S4q6d | 1,273 | 122 (all under 256 bits) | 0 |
| KV plan_c | 530 | 1,476 (1,452 under 256 bits) | kv3_hub_C 2 x 576, kv3_hub_Wo 2 x 1152 |

- The tool text itself records the HEAD measurement (`landing_placement.tcl`, DIE-HEAD-13): ring FIRM in netlist order
  676,805 GRT overflow on hd_tile, flops-only FIRM -97 % (REPORTED by that comment).
- B6gsl bands for the same types: t65 ft0_i 23.8 x 228.8 = 5,440 um2. The B6gE record says the ring needs 8,105 um2
  with the count-aligned reserve. So the B6gsl rect cannot hold the ring; it is not a known-good state for a 1152 ring.

Second factor (MEASURED, B6gG3b plan against `ft_slots[].in_window_um`): of 127 types with a wide ring on an ft slot, 47
have a band that leaves its pin window by more than 60 um along the face, 15 by 200 um or more. Example t65: ft1_i
pins y 248-487, band y 458-683, and the ft0_i band (y 17-456) lies across the ft1 pin window. The cores next to that
face leave a street of 75-106 um (vp_g_ln_6 / 7 / 14 right edges at x 1363 / 1333 / 1350), so both bands fit in front of
their own pins at 62-75 um depth. The composer grew the band along the face instead of in depth.

Root cause. The whole ring (about 25k-30k cells for 1152 bits) is packed FIRM in netlist order and spread to fill the
band. Cells of one bit land far apart, so every net of the ring crosses the band. Global placement cannot repair it
because the cells are FIRM. Band alignment adds a 200 um vertical detour on 47 types but is not the main cause (t1).

Fix.
1. **Rows, DIE-S81-92 (compose in F2s):** `ring_place: "ff"` on every S81 band of 256 bits or more (the tool picks
   `+ffr` for `lsb_high` buses). `OT_CLAND_PINSLOT = 1` is already in the S81 kits and becomes active with the tag.
   No RTL, no cycle, no lane change. Bands with `rects_um` (21 multi-rect bands) are excluded by the tool today; list them and make them single
   rects in the same event.
2. **Proof before the family, new Sonnet lane S81-RING-FF:** two kits, place + CTS + GRT only, from the converged S81
   tree: t1 (aligned bands, isolates the placement form) and t65 (misaligned bands). Pass = GRT 0 overflow, and the
   place log prints `OT_CLAND pinslot ... ring flops next to their ... bit pin`. Read FF hold on the ring write flops
   in the same kits, because the flops move.
3. **Composer rule, S81-CA-BAND:** grow a band perpendicular to the face first, up to the nearest hard core; keep its
   along-face span inside the pin window plus 20 um; raise `band_use_target` to 0.65 before leaving the window; only
   then ask for a core move. Re-compose the 47 types.
4. **Do not gate the y-slot rows on the bands.** After item 2 passes, S81-LEAF-PLAN reruns the 13 y-slot kits once.
   t62 (ft 48 %) and y-slot t34 (ft 35 %) keep a real ft share and need the ft read as planned.
5. **Fallback form, in parallel only if item 2 fails on t1:** a hard ring core for the 1152-bit E / W and N / S buses
   (KV precedent: `kv_cland_w269` ring cores are signed). One master per face orientation covers the 93 types.
6. KV-102: add `ring_place: "ff"` to hub_C and hub_Wo before their first place.

### Lever 2. Converged trees: verified, one gap

Evidence (MEASURED): key counts in section 1. `core_pin_lead` is absent from `src_s81_pin_e594a73db756`, because
claude/s81-col-clk-1116 was approved at 01:04 against main 7ce1e8344eb, after the tree was cut. Spec 0b
(`tap_window_measure.py`, b82b6c5dc1d) is READY, not merged.

Consequence: F2s rows `clock.core_pin_lead_ps`, `clock.tap_core_src` and the per-port window rows would be rejected by
the schema or ignored. This is the 23:15 lever 1 class again.

Fix.
1. TOOLS-CONVERGE-1115: rebuild the S81 tree from the main that contains s81-col-clk-1116 at b82b6c5dc1d, before
   DIE-S81-92 composes F2s. QC and HEAD keep e594a73db75.
2. KIT-OPS-5: accept test per die on one fresh kit, unchanged from 23:15 (M7 offset 8.448, a `tt_setup_repair*` file,
   `pg_pair_cap.tcl` last in `grt_pre.tcl`), plus for S81 a `core_latency.txt` ROM row at 255 and
   `OT_RC_SIGNAL` in `config.mk`.
3. Bind and wave must read one source root per die (HEAD built kits from c327 while the bind proved rp21z20; REPORTED).

### Lever 3. S81 col: order of work

Evidence (REPORTED, FABLE-FIX-S81-COL, CTS stage, signal C x1.45): wave kit 1,476 endpoints / -380.6; four-part form
144 / -199.8; tap means 348..478 on the F2r pilot. With the kit SDC (flat 165 ps window on 26 grid ports) 6,543
endpoints / -340.6; window 0 gives 26 / -175.6 and FF hold 518 / -121.5 before repair. Measured per-port windows
(spec 0b, pilot CTS log): p50 10, p90 41, max 76 ps.

Judgement: direction right. Order:
1. Rows on the 216 types (DIE-S81-92): nearest tap, `tap_max_sinks` 3000, core sources from the tree, ROM lead,
   `reset_relay_full`. ROM lead 300 instead of 255 is worth one CTS read (read side -3..-5 at 255, address side had
   +348).
2. Per-port window rows from the pilot `4_cts.odb`, then from the family. Caution: the measured window is the sink
   range inside the type. The die tree must deliver the same ports inside that window; S81-TAPROWS states the die-side
   number per port before the rows are adopted, otherwise the type passes and the die pair check fails.
3. The 26 endpoints at window 0 are three structural classes with specs: go_tag half-cycle face (4), element
   `sh_free` / `bank_free` to s `ef` (4 at -119), reset copies (3 at -59). Specs 1-3 in parallel, not after.
4. Hold: 518 endpoints at -121.5 pre-repair are cross-tap pairs. Read them after the per-port windows; pad only what
   remains.

### Lever 4. HEAD

Evidence (MEASURED).
- hd_st_k5, kit `fable-fix-head-types/k5a`: wrapper RTL has `.WFALL(1)` x4 and no `.FREG`. SDC:
  `set_input_delay -max 699.72 -clock fclk_in_d_i d_i[*]`. Path `d_i[269]` -> BUF -> AO21 -> `sd_c[77]` (falling-edge
  flop): 59 ps of logic, required 538.0 (fall edge 416.5 + 130 tree), arrival 758.6, slack -220.6. Plan NF13a:
  hd_st_n4 has `clock.landing_ring_wreg.freg = true`; hd_st_k5 has no `landing_ring_wreg`. This agrees with the lane's
  READY-ROWS of 01:13 (which adds hd_st_turn).
- hd_serdes, kit `sd2`, `postcts_gate_TT.log` by path group: clk -62.05, **pma_rck -127.85**, others met. The pma_rck
  path is `u_dec.u_syn.ldr[1][0]` -> `g_bm[1].u_bm.d[8][7]`: 949 ps of data in the KP4 decoder, with nets of 21, 32
  and 41 loads (102 fF on one BUFx6f). `tt_setup_repair_grt.log` ends at wns -43.92 on the same database.

Root cause. k5 / st_turn: a falling-edge writer without the rising face register has a half cycle the contract does
not give. serdes: the repair step's WNS does not include the recovered-clock group, so that cone was never repaired;
the cone itself is a fan-out problem in the decoder.

Fix.
1. HEAD-100 (NF13b): the FREG rows as posted; +1 cycle on those lanes, bind + LATCHECK. Add a gen check: a ring in
   `ring_hold.write_fall_types` without `freg` is a gen error.
2. FABLE-FIX-HEAD-TYPES: make the TT repair read and repair every clock group (print WNS per group before and after).
   If pma_rck stays under -42: replicate `ldr` per BM cell group in the decoder RTL (no cycle), then a pipeline stage.
3. he3 / hw3 gate at -10.5 / -9.7 on unadjusted RC: see lever 7 before they are counted on.

### Lever 5. QC

Unchanged in direction (FABLE-PD-QC-S4q8). P0 is the proof to read at sign-off. P2 stopped in `3_5_place_dp`; if kept
hierarchy is the cause, use placement groups on name patterns of the flat netlist instead. P1 and the 9 placed
`DRT-0255` types need the tree switch (lever 2). QC rings are all on the flop-only form (lever 1 table), so QC is not
exposed to the S81 ring class.

### Lever 6. KV

Direction right (REPORTED): ring child cores take pv types from 635k placed cells to 211-258k by plan estimate. The
400k decision is taken on the placed census of the pilot, not on the estimate. hub_C and hub_Wo carry four wide rings
without `ring_place` (lever 1 item 6); no hub type has reached place.

### Lever 7. RC coverage and svc memory

- HEAD and KV have no entry in `rc_signal_scales.json` (REPORTED, r258). Unadjusted gates under-read by 118 ps (S81
  col) and 181 ps (QC hc2). INFERENCE: HEAD gate reads near -10 can be about -100 routed. GENBUG-IMPL fits HEAD from
  the routed SPEF of a signed HEAD type (hd_spn, hd_tile) before he3 / hw3 are read as passes; same for KV on q2.
- The core flow is not wired to the x1.10 entry (REPORTED), so bksel fx1 / fx3 depend on the lane's private scale.
- S81 svc (16 types): the staging memory is 4 x 160 x 265 bits of flops (42,400 DFF per instance) and fails the
  synthesis memory check. GENBUG-IMPL's third branch (4 x `ot_sram_1r1w_160x265`, same read latency, 15.5k um2
  against 26k) is the right form. COORD gives the go; S81-SVC-SYNTH sets `SRAM_MACRO=1` on the svc types.

## 3. Stop list

1. S81-CA-BAND re-placing or `BAND_RESTORE` of B6gsl rectangles as the fix for the 13 y-slot kits: t1 fails with
   aligned 71 um bands, and the B6gsl rect is smaller than the ring.
2. Any rerun of S81 kits with 1152-bit rings (leaf, svc, slice, col r0) before `ring_place: "ff"` is in the plan.
3. More GRT iterations or a removed early stop as the answer on those kits: 180k-250k overflow inside FIRM cells.
4. Composing F2s on the e594a73db75 S81 tree.
5. Releasing any col kit on the flat 165 ps window; adopting per-port windows without the die-side number.
6. TT repair or relaunch of hd_st_k5 / hd_st_turn without FREG; reading hd_serdes from the repair WNS line.
7. Counting he3 / hw3 as closed on an unadjusted gate read.
8. Still valid from 23:15: route-keep ECO on cores at -150 or worse; hc2 closed on a gate read; `BANK_PIPE` now; KV
   v20 / v21, PVGEN 2-way, pv kits on kvgeom6, 7p; releasing pv_v1n on 7yh.

## 4. Not checked

- No kit has run with `ring_place: "ff"` on an S81 1152-bit ring. The -97 % figure is HEAD's, from the tool comment.
- Why t23 showed only 30 overflow gcells on 11-14 (FABLE-TYPES-S81-LEAF): band and ring size of that build not read.
- Whether the 21 multi-rect S81 bands can become single rects.
- hd_st_n4's gate (+83) and the k5b proof: not read by me.
- The P2 failure cause; the P0 route state; bksel fx1 / fx3; KV 7yh and r3n gate results.
- METHODOLOGY section 12 has no rule on the ring placement form; none of the fixes above conflicts with it as far as
  I read (headings and landing terms only).
