# FABLE-CLOSURE-STRATEGY 2026-11-17 07:30 PST (0730): delta on 03:20

Reviewer: FABLE-CLOSURE-STRATEGY-0730 (Fable). Read-only on builds, no probe jobs launched (logs and reports only). Technical PD only. HBM parked.
Blocking gates (R-MINIMAL): DRC 0 route, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.

Marking: **V** = I opened the file / log myself this round. **R** = reported by the named lane or Fable report, not opened. **P** = my proposal, not measured.

## 0. What changed versus 03:20

1. **S81 SerDes H12 is not a failed form (V).** Post-CTS TT, placement RC: -90.98 / TNS -659 on 9 ends before the TT repair, **+0.71 / TNS 0 after it (455 cells)**. The `OT_STB_SPAN 214 FAIL` is the 8-round cap cutting a sweep that was still converging, and a die-wide span is the wrong acceptance. H13 / H14 are brackets, not successors (lever 5).
2. **S81 col: the pg3 repair crash was a flow defect, not design (R, FABLE-PD-S81-0720).** The repair path leaves 3,967 PG-track obstructions in the GRT DB. With three flow defaults the 63 released members need no post-route ECO (lever 1).
3. **QC cb has exactly two classes and both have merged fixes (R + V of lane result):** stranded trunk (join through buffers; cross-check lifts the 5 ends to +313..+385) and `tap[0]` latch (bit-level `latch_except`). Port-wide `latch_except` is refuted: 1,744 of 1,776 pins fail hold.
4. **QC M5 is adopt-ready, but the clock rows move with every tree re-cut:** 112 of 133 types leave the L2 tolerance. Clock of record + one event N is the structural answer (lever 2). D3 loses 21 types/h to a kit_rtl path class; D4 fixes it.
5. **S81 strip: the t34 overflow is a 30-um seam, and the census finds two more exposed leaves** (t71 1.33, t13 1.29, t34 1.12) (R, S81-DIE-R3).
6. **HEAD NF15f: neither hop halving nor growth closes alone; both together assign 40,670 / 40,670 trunks** (R, HEAD-R3). hd_ctl and hd_st_n3_turn are signed off.
7. **KV D16 fresh gates PASS and the publish result is printed (V).**

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| S81 H12 CTS balance | epyc2 `/srv/opentallas-scratch3/claude/fable-fix-s81-serdes/H12/serdes__t13/gen/serdes__t13/run/logs/asap7/dp_serdes__t13/base/4_1_cts.log` lines 2355-2611 | Before: 25,112 sinks, min 1648, p1 1879, med 1899, p99 2043, max 2216 (spread 567, p1..p99 164). Rounds 0-3 pad 8 nodes each; round 4: 20; 5: 21; 6: 73; 7: 107. Spread 567 -> 501 -> 463 -> 437 -> 424 -> 411 -> 399 -> **280 -> 214**; p1..p99 168 -> **112** in the last round. 428 INV pairs. Stop reason: `OT_STB_ROUNDS` = 8 |
| Balance algorithm | same kit, `subtree_balance.tcl` lines 10-24 | Top-down: pads the highest early node, at most 12 stages a node a round, nodes below a padded node wait for the next round. Target = latest sink, fixed. Rounds default 8, tolerance 8, stage 20 ps |
| S81 H12 post-CTS TT | same kit `tt_setup_repair.log`, `tt_setup_measure.log` (07:08-07:09) | Before -90.98 / TNS -659.36, 9 violating ends; 495 slew violations (497 buffers); after: 43 buffers removed, 1 inserted, 3 resized -> **+0.71 / TNS 0.00**, measured again from the written DB. Stage now in pre-GRT FF hold. No GRT read yet |
| S81 H12 CTS json | same, `4_1_cts.json` | ws -83.94, TNS -607, 19 setup ends, clock skew setup 481.75 (all clocks, before the TT repair) |
| S81 H13 / H14 | epyc2 same lane, `H13`, `H14` | Both in `4_1_cts.tmp.log` at 07:11. H14 log: pin box moved dx 1,115.328 um in the odb only |
| KV D16 | intel2 `~/tmp/kv-r3/d16_gate.log`, `d16_publish.log` | Unit exit 0, `KV_D16_READY` plan 340b90be33dd, manifest d9187b9c24f1; `D16_FRESH_GATES_PASS`; `PUBLISH_RESULT` printed. I did not read the verdict field |
| QC cb cross-check | intel2 lanes/posts/QC-TYPES-R3.md 06:56 | Lane result (R): tap_d[431] +319.7, [439] +333.7, [442] +313.4, [465] +363.9, cap[10] +384.8; left: u_t13/tap[0] -100.2, u_t03 -95.9, u_t02 -85.9, u_t12 -63.3 |
| Failure classes | intel2 `tools/failure_breakdown.py` 07:12 | S81 types 41 / 394: kit_rtl 28 (dsdv_slice_c1x_C), kit input missing 7 (bk_sel), other flow 7, congestion 1 (phy__t1), place error 1 (serdes__t3), hold after CTS 1 (serdes__t4). QC 8 / 127: kit_rtl 25, running 43. KV 6 / 56: 9 wait on child core, kit_rtl 1. HEAD 23 / 26 |

Not opened: any GRT or routed DB of today, the C4r3 plan, the NF15f witness files, the M5 plan, the KV HG6 row packet, the col route-only retry.

## 2. Levers, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: three flow defaults before the first route (PG obstructions out, hold margin 15 / 10, M5 block over sstn) | 203 col types (63 h9_r2 + h10_r2 released now) | S81-TYPES-R3 |
| 2 | QC | M5 on D4 tools; clock of record; one event N | about 112 types to re-sign, die bind, 21 fails/h | QC-PLAN-R3 |
| 3 | KV | apply D16; HG6 = bays carve + ring->bin stations in one event | 50 unsigned types (9 wait on a child) | KV-R3 |
| 4 | QC | cb: join through buffers + `tap[0]` bit latch_except + sized pad | 18 cb types / 192 partitions | QC-TYPES-R3 |
| 5 | S81 | SerDes: H12 to GRT; pair-skew acceptance; rounds 16 if needed | 11 serdes types | S81-TYPES-R3 |
| 6 | S81 | strip seams: VE moves for t34 / t71 / t13 + blocking channel check | 3 exposed + 4 marginal of 74 strip leaves | S81-DIE-R3, S81-TYPES-R-STRIP |
| 7 | HEAD | NF15f as one geometry event; reserved-site carve in the generator | hd_lep0N, hd_mesh, hd_serdes + die gate | HEAD-PLAN-R4, HEAD-TYPES-R4 |
| 8 | S81 | cores: bksel merge (+1 cycle) and gunit bf record, in the same next tree as lever 6 | S81 die function, 2 cores | S81-DIE-R3 |

### Lever 1. S81 col (203 types)

Evidence (R, FABLE-PD-S81-0720, each row V there): pg3 routed TT -39.25 passes. What fails is internal FF hold 57 ends at -7.61 (50 of them one class: hard-core `u_s13` output into its first flop) and 2 M5 shorts inside sstn core t6. The repair run died in DRT-1231 because `OT_PG_TRACK_TRUTH` added 3,967 temporary obstructions and the repair path never removed them: 15,736 static spacing violations on M5 / M6 / M7. The route-only retry without them converges 686 -> 46.
Root cause. (a) flow: obstruction removal exists on the first-route path only. (b) hold is closed to +5 ps on placement RC and 0 on GRT RC, and detail route takes 8 to 12.5 ps. (c) GRT sees free M5 tracks between the 817 obstruction rectangles of the sstn abstract that detail route cannot use.
Fix (S81-TYPES-R3, with TOOLS-CONVERGE for the flow file).
1. Remove PG-track obstructions before every `5_1_grt.odb` write; check per-layer obstruction count equals the seed before detail route.
2. Same-tap margin 5 -> 15 ps pre-GRT, GRT repair margin 0 -> 10 ps (`OT_HOLD_FF_MARGIN`); price hard-core output starts with the cross-tap guard. Setup room on these ends is 690 ps.
3. M5 routing block over every `ot_s81_sstn_*` interior from floorplan (inset 4.0 / 2.0 um).
4. Members already routed: route-only hold insert (78 cells on pg3) with item 1 in.
Launch order: items 1-3 are defaults in the tree the released 63 members build from. A member that reaches GRT before they are in is a known repair, not a new failure class.

### Lever 2. QC M5, D4, clock of record (die-wide)

Evidence (R, FABLE-PLAN-QC-M5): M5BR bind 0 errors, LATCHECK 1,921 / 1,921, CB16 468 / 468, G0 0 errors. M4 -> M5 diff is 5,748 keys, all under `clock.*`; only 3 st_b types are justified (382 rows, up to 32.2 ps), 11 types moved 1.1 ps or less. M5 against L2 rows: 112 of 133 types out of tolerance (6,034 ports, up to 57 ps). The die STA is tree-on-model (0 kits, 0 views). D3 (R, QC-PLAN-R3): about 17 types failed kit-rtl since 05:15 on 50 absolute paths of the old pin tree in the L2BQ `bind.f`.
Root cause. `rows_m.py` rewrites every row at need + 10 with no hysteresis, and every plan event re-cuts clock regions, so rows drift past tolerance on types the event did not touch. Each drift costs a rows fold, a tag, a 60-minute bind and a die-wide re-sign.
Fix (QC-PLAN-R3).
1. D4 = D3 + `bind.py` with main 3d763393b4. Publish when the 4-type repro passes; release the D3 hold.
2. Publish M5 as D4 tools + M5 plan after the A1 check (gen_phys tables on 133 types, kit-rtl on 22 param_wrap types). Not from treeJ.
3. Clock of record: freeze `s4q9m4/kit/clock/tree.json` + `rows.json` by tree sha, outside the plan tag. Later events re-cut only regions whose tap set changed; a row is rewritten only when its gate fails.
4. One event N on that tree: bit-level `latch_except`, N START, SC reset, R-REACH-4. Not four events.
5. Build order after adoption: the 3 st_b types and the 5 st_a masters first, since their rows are the ones real views will move.

### Lever 3. KV (50 unsigned types)

Evidence: D16 gates PASS (V). 9 types wait on a child core (V, breakdown). PC (R, KV-PC-DELTA): 20 buses ring -> bin over 405 um, worst `i_slg_Q_N_af__fault` 1,436 um, `i_kvs_emb_px_tok` 888 um; ring bank in the east strip x 916-1015, bins at the face pins; 25 stations proposed, form not confirmed. Blanket channel keepouts collided with 12 planned START / reset bays; the bays-only carve keeps 36,718 of 36,984 um2 with 0 collisions.
Root cause of PC: the ring bank is on one edge of a 1036.8 x 1520.64 type and its consumers are on the faces. That is distance, not placement quality.
Fix (KV-R3).
1. Apply D16 with pilot kv3_hg_v1 now; the 9 child-wait types launch from it.
2. HG6 is one event: bays-only carve + the 25 ring -> bin stations as `internal_stations`, cycles priced in LATCHECK. Stations are the scripted form (reach rules) and need no core re-shape.
3. Take the bank re-site (east strip to the type centre) only if a station cycle breaks a latency group in LATCHECK. P: at the centre the worst hop is about 760 um, still 1 station, so it does not remove the cycles; it only halves them.

### Lever 4. QC cb (18 types / 192 partitions)

Evidence (R, FABLE-PD-QC-0600, V there): 42 heads / 81 stretched paths; joined path 411 ps (+353.9), stranded 837 ps (-70.0). `tap[0]` has its own core arc (setup 216.8 / hold 641.8): window 261 to 624 ps after the edge. Without the latch: setup +294.7..+338.3, hold t12 -13.8 TT / -14.0 FF.
Fix (QC-TYPES-R3; plan row by QC-PLAN-R3 in event N).
1. xj_join result decides the join fix; the cross-check already shows the class closes.
2. Plan row `{qfd_tile_nk_a0c: ["tap[0]"]}`, never `["tap"]`.
3. Pad the 4 `tap[0]` nets by 120 to 170 ps TT with an explicit `hold_pad_hb4` row. Do not leave it to generic hold repair: the window is 363 ps wide at one corner and the target must sit at both corners, which repair to >= 0 does not aim for.
4. Gate for the wave: 0 `b_d` ends below -42, `OT_XSTN_STRETCH` 0, the 4 `tap[0]` pins setup >= +100 and FF hold >= +50.

### Lever 5. S81 SerDes (11 types)

Evidence (V, section 1). H12 is H5 placement + rck balance. The balance tool works top-down and touched 8 nodes a round for four rounds; it reached the wide levels only in rounds 6 and 7 (73 and 107 nodes), where the spread fell 119 and 66 ps a round and p1..p99 fell to 112. It stopped on the round cap, with 428 pairs of a 4,000 budget.
Reading. S81-TYPES-R3 07:02 recorded a model error (bulk p1..p99 175 against 107 assumed). The last round reads 112, so the bulk is close to the 0600 figure once the deep levels are padded; the 164-181 of the earlier rounds was the unpadded early tail inside the percentile band. Second, the H5 failure was a 415 ps adverse pair (launch 72 stages, capture 63). After H12 the earliest sink is 2003 and the latest 2217, so no pair can be more than 214 ps adverse, and the bulk-to-late case is about 45 ps (median 2173). The `x0 -> x_q` class had -64.25 with 415 adverse.
Fix (S81-TYPES-R3).
1. H12 goes to GRT as the lead form. Acceptance is the GRT TT read by class, not `OT_STB_SPAN`: by the owner's clock rule the gate is related-pair skew, not max-min spread. Replace the 110 ps span line with: worst launch-capture insertion difference on rck paths under +60 ps slack.
2. If a clock-skew class is still under -42 at GRT: rerun CTS with `OT_STB_ROUNDS=16`. Config knob, no code. P: two to four more rounds at the round-7 rate bring the span near the tolerance.
3. H13 (slew gate 165 ps, drops about 128 repeater chains) and H14 (centre pin, odb only) stay brackets. Do not promote either before the H12 GRT read.
4. Centre-root trunk rows: only if the routed AM class (`rxf_q` fall -> `face_am3.parts`) is under -42. It was -15.0 at H5 GRT.
5. P, cheaper than the trunk for the AM class: build the 20-stage rck trunk from inverter pairs. Duty distortion is 2.35 ps per same-polarity BUF stage (148 ps at the median sink); alternating polarity cancels it per pair. The balance pads are already inverter pairs.
6. serdes__t3 (place error), __t4 (hold after CTS), t12 and the G / J types are floorplan-blocked (R) and not this clock.

### Lever 6. S81 strip seams

Evidence (R, FABLE-PD-S81-0720 V there; census R, S81-DIE-R3): t34 west seam 30.37 x 345.6 um, 1,766 station flops of five ft slots on 1,385 GRT-usable vertical tracks; overflow M6 2,199 + M8 1,254 is the macro edge the spill crosses. Census on the C4r3 plan: t71 1.33, t13 1.29, t34 1.12 exposed; t10 / t74 0.69, t75 0.66, t39 0.61 marginal; t62 0.25.
Fix.
1. S81-DIE-R3: next-tree rows t34 +34.56, t71 about +43.2, t13 about +51.84 um (VE_m and VE_s together, target 0.6). 0 flops, 0 cycles.
2. S81-TYPES-R-STRIP: the per-channel ft track read becomes blocking before GRT, summed over all slots of a channel, fail above 0.70.
3. Spread each station over the seam width as columns.
4. Form-B pilot is t62. The other 67 leaves at 0.53 or less do not wait for the VE rows.
5. One next tree carries lever 6 rows, lever 8, and the rck trunk rows if lever 5 item 4 fires. Not three trees.

### Lever 7. HEAD NF15f

Evidence (R, HEAD-R3): worst cut x 980 holds 8,627 tracks for 5,710 mandatory; stage hops of 300-389 um leave a 9-45 um legal y window under 405 um reach. Halving alone 1,617 unassigned; +60.48 alone 6,281; both 0 of 40,670 at 78.75 %. Cycle tuple composed: bind PASS, LANE_ASBUILT 329 / 329, G0 0 errors. hd_serdes sd9f: 28 DRC, all reserved-site obstructions over clock-tap pins (19 M7 shorts + 9 M2 spacing), the he12h class (R, HEAD-TYPES-R4). Mesh PG 141 -> 7 with local tracks; the 7 are pin access inside 2 reserved die-clock-cell sites.
Fix.
1. HEAD-PLAN-R4: one geometry event: +181.44 on the LEP upper pair, relay anchors at the witness columns, mesh `OT_PGCAP_FINITE_EXTENT` + `OT_PGCAP_M5_LEGAL_TRACKS`, the north 2-node clock re-site, fresh clock GEN and reset census. Rerun the allocator on the composed plan before any kit.
2. The trunk witness is horizontal only. Before kits, add the vertical branch and pin-access read at the 12 relay columns (x 537.5 .. 1649): 15,031 relay flops in columns is the same shape as the S81 t34 seam. Apply lever 6 item 2 (0.70 of usable tracks per column channel) there.
3. Regenerate the token / compiler calendar for the tuple (PIN +2, POUT +4, TXI, KTX, KRX): a cycle change is a functional lane item and blocks.
4. Reset seams (714 / 530 FF fails, R; I did not open the census): redo the census on the NF15f clock, not the old one. Seams with setup + hold window >= 0 take the last relay into the receiver region; the rest take a negedge relay with the hop under 180 um (R-REACH-5). Region skew p90 of 896 ps (03:20) rules out plain hops.
5. HEAD-TYPES-R4: sd9f ECO as running. Then make the carve a generator rule: reserved-site obstructions leave the tap pin access stack open on M2 and M7 at floorplan. hd_lep0N and hd_mesh get new kits in the event and would repeat the class a third time.

### Lever 8. S81 cores

Evidence (R): bksel has two source forms (stations with and without RFH / HLAT); the merge gives RFH 2 = +1 cycle on lane / f_c / f_cr -> t_s / t_o, so `dsfd_selt_c` waits take +1. C4 keeps the D5c hq3 view. gunit: BA1 FWPPK signed off (TT +0.74, FF +6.86), bf has no kit-wave row (V).
Fix (S81-DIE-R3). bksel merge with bench + mutant and LAT price in the next tree (lever 6 item 5). Registry entries carry view scope (the D5e-r3 bind failure was a module-keyed fallback). gunit bf record row. The define-set check of 03:20 lever 5 still stands and is not built.

## 3. Fundamentally hard families

| family | limit (measured) | structural change |
|---|---|---|
| S81 SerDes rck | One recovered clock entering at the west end of a 2,246-um PMA strip: 63 stages, 2.18 ns, 2.35 ps duty loss per BUF stage, half-cycle paths get 192-268 of 416 ps | Depth balance (in), inverter-pair trunk (P), centre-root die trunk as last resort; no new half-cycle hops in RTL |
| S81 strip west seam | 1,766 to 2,534 ft bits turning in a 30-43 um seam: 112-133 % of usable tracks | Seam width by VE move; blocking channel check at plan time |
| S81 col | Legal relay sites between paired macros; hard-core output -> first flop hold loses 8-12.5 ps in route; abstract M5 gaps | Plain posedge relays, margins before route, full M5 block over sstn |
| HEAD LEP corridor | 300-389 um hops under 405 um reach: 9-45 um y window for thousands of nets | Hop halving (cycles) and +1.03 % die area together |
| KV PC ring -> bin | 888-1,436 um against 405 um reach, bank on one edge | Stations (cycles); bank re-site only halves them |
| QC cb `tap[0]` | Core pin window 261-624 ps after the edge with an early core tap; other bits 329-1,079 | Per-bit lockup choice and a sized pad at both corners |
| QC die clock rows | Rows cut on a model die, re-cut every event: 57 ps drift on 112 types | Clock of record keyed by tree sha |

## 4. Stop list (changes; the 03:20 list otherwise stands)

1. S81 SerDes: `OT_STB_SPAN` 110 as a gate or as a reason to drop H12; H13 / H14 as closure forms before the H12 GRT read; centre-pin plan rows before a routed AM read under -42; density variants; data-side AM fixes; xface retime as closure form.
2. S81 strip: GRT or GRT tuning of form-B t34 on the current floor; holding the 67 unexposed leaves for the VE rows.
3. S81 col: the prd-path repair before the obstruction removal is in; a blanket M5 block on a routed DB; per-member post-route hold repair on members not yet at GRT; reset RTL or pin-access changes.
4. QC cb: port-wide `latch_except`; more join rounds; a +1 cycle station or a re-site; generic hold repair as the `tap[0]` pad.
5. QC plan: rows re-fold or a new bind for a rows-only delta; M5 cut from treeJ; L2 launches of M5-changed types; separate events for latch_except / N START / SC reset / R-REACH-4; quoting +403.6 as die setup.
6. HEAD: growth only or halving only; M8 grant widening; time-multiplexing; a third per-type ECO of the reserved-site class without the generator rule; reset seam work on the pre-NF15f clock; an unchanged hd_mesh rerun.
7. KV: blanket channel keepouts in pc; publishing D15; repair or sizing on ring -> bin paths; a bank re-site as a way to avoid cycles.
8. All dies: three separate S81 next trees (seam rows, bksel, rck trunk); kit relaunch on a row move under tolerance.

## 5. Not checked

- H12 GRT or routed timing: the +0.71 is placement RC after TT repair; H5 read worse at GRT than at CTS on the skew class. The 45 ps bulk-to-late figure is arithmetic from the round-7 percentiles, not an STA of pairs.
- Whether rounds 8-16 keep the round-7 rate; the inverter-pair trunk; both are proposals.
- The seam census, the NF15f witness, the HEAD reset seam census, the KV ring -> bin table and the col route-only retry: lane reports only.
- KV `PUBLISH_RESULT` verdict field; the D4 repro; the M5 A1 check result; xj_join.
- S81 kit_rtl 28 (dsdv_slice_c1x_C) and kit input missing 7 (bk_sel): I did not open one failure log; they look like the QC path class and the bksel view scope, not confirmed.
- Vertical capacity at the NF15f relay columns: flagged from shape, no count.
