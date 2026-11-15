# FABLE-ROUTE 2026-11-14 22:55 PST: routing and congestion, all four active dies (type level and die level)

Owner request: "let fable review the routing and congestion overall". Reviewer: Fable, read only. No build was started,
stopped or changed. HBM is parked and not covered.

MEASURED = read tonight from a log, report, LEF, guide file or kit file. INFERENCE is marked.
Extracts (one JSON line per attempt): rtx-pro
`/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/fr/` (`all.json`, `cong_*.jsonl`, `kv/*.jsonl`).

Sample: every attempt still on disk under `kw43-wave-1109n/runs` (S81, HEAD, QC) and `kw43-wave-1109/runs/qwen_kvsys` (KV)
on intel1, intel2, epyc2, epyc7, epyc8, epyc9, epyc10. 1,229 attempts; 635 have a global-route log, 189 a detail-route
log, 379 a congestion report. Cleanup has removed older attempts, so counts are "of what is on disk", not of all history.

## 0. Verdict

1. Routing capacity is not short on any die. Median layer use after global route is 4-10 % of the type, and M4-M7 are
   under 10 % in almost every family (section 1.1). No failure in the sample is a full die or a full type.
2. The failures are local and of four kinds: (a) one free layer per direction above hard cores, (b) the pin band at the
   type faces, where pins, PG pairs and the first register rank meet, (c) cells added by the wire-length rule, (d) the
   flow treats a small remainder as fatal and then repeats the same build.
3. The architecture (abutted types, feed-throughs inside the types, M8/M9 for die clock and PG) is right and matches
   industry hierarchical practice. I would not change the layer split. Two things in the die-level proof are wrong and
   make its numbers easy to misread (section 2).
4. HEAD's 50.9 m is not die-top wire. 97 % of it is feed-through nets that belong to the types. The real die-top signal
   wire on an abutted die is zero; the die owns clock, reset and PG only.

## 1. Type level

### 1.1 Where attempts end (MEASURED)

| die | reached GRT | GRT fatal on overflow | reached DRT | DRT-0255 | DRT-0206 | few DRC left | DRC 0 |
|---|---|---|---|---|---|---|---|
| S81 | 344 | 149 (GRT-0116) + 13 (GRT-0232) + 10 (GRT-0183) | 17 | 12 | 0 | 0 | 3 |
| QC | 130 | 9 | 62 | 17 | 14 | 16 | 7 |
| HEAD | 86 | 0 | 75 | 19 | 0 | 2 | 50 |
| KV | 75 | 29 (GRT-0116) | 35 | 11 | 0 | 1 | 23 |

Layer use after global route, median per family (usage % of the layer's own capacity):

| family | M2 | M3 | M4 | M5 | M6 | M7 | M8 | overflow share |
|---|---|---|---|---|---|---|---|---|
| S81 col_r1 (123) | 17 | 12 | 14 | 7 | 9 | 4 | - | M6 95 % |
| S81 col_r0 (8) | 23 | 12 | 16 | 6 | 10 | 5 | - | M6 93 % |
| S81 leaf (66) | 6 | 11 | 4 | 6 | 4 | 5 | <1 | M6 60 %, M8 27 % |
| S81 slice_station (34) | 2 | 9 | 1 | 1 | 1 | <1 | - | M3/M5/M7 90 % (vertical) |
| QC cbn / cbx / cbf (8) | 6-14 | 16-31 | 3-8 | 7-15 | 3 | 1-3 | <1 | M6 68-90 %, M8 10 % |
| QC relay (stm, fw, fe, sc) | 17-26 | 21-31 | 3-4 | 4-6 | 1-4 | 1-2 | <2 | none |
| HEAD (all 16 families) | 0-15 | 0-19 | 0-8 | 0-9 | 0-7 | 0-3 | 0-2 | none |
| KV hg / hgi | 13-22 | 10-23 | 7-14 | 5-14 | 3-7 | 2-4 | 1-3 | 29 to 503 gcells in total |

Detail-routed wire sits on M2 and M3 (leaf: M2 1.17 m, M3 1.32 m, M4-M7 1.56 m together; QC sle_fw: M3 6.8 m of 12.1 m).
The upper layers are nearly empty because the wire-length rule cuts every net to 33-120 um, and short nets do not climb.

Capacity taken before any signal is routed (kit `pdn.tcl`, `pg_track_truth` line in the GRT log, col_h10_r1):
- type PG: M5 pair 0.12 / 0.072 at 4.32 um, M6 pair 0.288 / 0.096 at 4.32 um, M7 pair 0.288 / 0.096 at 8.64 um;
- tracks that detail route cannot use beside these pairs: M5 3,707 of 14,828 (25 %), M6 944 of 5,664 (17 %),
  M7 332 of 1,992 (17 %);
- GRT "reduction" printed: M2 29 %, M3-M5 26 %, M6 31-32 %, M7 32 %, M8 29-31 %. M3 carries no PG, so 26 % there is
  the blanket 0.25 layer adjustment.

### 1.2 Mechanisms

**A. Small remainders are fatal, and the same build is repeated (MEASURED).**
- 563 of 591 `global_route` commands run without `-allow_congestion` (28 have it). 200 attempts ended on
  GRT-0116 / GRT-0232, 10 more on GRT-0183.
- S81 col_h9_r1: 102 attempts ended GRT-0116 with "26,865" overflow. The final `congestion.rpt` of these kits holds
  4 gcells and 5 nets (`u_lpl_11_w.q[6]`, `q[246]`, `q[248]`, `q[251]`, `net134716`), all capacity 0, vertical, at
  x 464.0-466.3, y 1094.4. That point is 1.3-3.5 um inside the east edge of core `u_e8w.u_view.u_c`
  (`ot_v41_bf_col3_c`, 208.2 x 198.7 um at 259.3, 959.1; obstruction M1-M6, 777 M4 pins on the east face).
  The 26,865 is the per-layer table after layer assignment (M6 26,063, largest single edge 12); the 2D route had
  converged. Example: intel1 `.../col_h9_r1__t1__cl49d7a23e__pvbb600efe/attempt_4`.
- The same kit shows the iterations: 5,730 congested gcells at iteration 5, 75 at 10, 11 at 15, 4 at 20, 25 and 30.
  GRT ran 3 h 22 min; the last 1.6 h changed nothing.
- Other col_h9_r1 variants pass the first GRT with 0 overflow and then stop on GRT-0232 in the incremental route with
  44 (M5 24, M7 14). So the family is at the edge, not behind a wall.
- KV: all 29 GRT-0116 attempts have under 1,000 overflow (9 under 100; hgi_v1 31, hgi_v2 96, hgi_v3 41) at 2-23 % use.
- S81 slice_station: 18 of 34 attempts, median 1,025, vertical layers, in the pin rows at y 0 and y 1,166-1,227.
- Repeats without a kit change: HEAD hd_ctl_n `w3u_i[427]` same route box in 4 attempts; hd_host_e `od[142]` 2;
  QC coll_ucie `net309` 2; slw_hc2 `u_ist_cw_n2_0/net28212` 2; S81 slice_station t17 2.
- Not proven: that detail route closes the col_h9_r1 kit once it is let through. That needs one build (lever 1).

**B. One free layer per direction above hard cores (MEASURED geometry, INFERENCE for the size of each fix).**
- S81 col: 81-89 cores per type, floorplan use 46-50 %. `bf_col3_c` blocks M1-M6, so above it only M7 (vertical) is
  free and there is no horizontal layer at all. The other cores stop at M5, so M6 is the only horizontal layer above
  them. 95 % of the col overflow is on M6. The type ceiling is M7.
- QC cbn / cbx / cbf: four A0 tile cores of 457.9 x 1,157.8 um in a 1,235.5 x 2,531-2,566 um type, 67-70 % of the area.
  Core obstruction: M1-M5 99 %, M6 13-19 %, M7 1-12 %. 72-99 % of the reported congested gcells are horizontal cells
  with capacity 0 (10,000-11,500 per kit, the report cap). Ceiling M8 on cbx, M7 on some cbn kits.
- On both, M6 above the cores also carries the type PG pair every 4.32 um and the 0.25 adjustment.

**C. The pin band (MEASURED).**
- 59 of 189 detail routes ended DRT-0255 in iteration 0 (S81 12, QC 17, HEAD 19, KV 11: io_cor, io_ft_v1,
  sys_SD), with 13,000-250,000 violations at that
  point, after about 2 h of detail route (slice_station t8: pin access 9 min, track assignment 6 min, iteration 0
  1 h 49 min) on top of the GRT hours.
- Where (the 48 on S81 / QC / HEAD): 25 route boxes lie within 80 um of the west face (x 14.8-78.7); the S81 slice_station ones lie on
  the north pin row (y 1,199.9-1,223.8 of 1,226.9). Nets: type ports (`ft1_i[90]`, `ft2_i[232]`, `ft2_i[688]`,
  `w3u_i[427]`, `hr_ei[227]`, `b_hw_i[136]`, `t_i[104]`, `x_fw_ctl_p2_i[464]`), the first station rank
  (`u_ft_ft0_o_2`, `u_ft_ft1_o_2`, `u_ft_rsn_o_1`) and the landing-ring select cells (`u_cland_*/u_ring.dch[*].u_dsel`).
- `OT_PG_TRACK_TRUTH` does not remove the class: 16 of the 48 are kits that carry it.
- This agrees with FABLE-PD-HKQ Q1 and FABLE-PD-S81 lever 5 (PG pair rows against pins). What I add: the place is the
  face band, on all four dies, and the cost is one unroutable net per 10-14 h build.
- Pin access already runs before GRT and caught 18 attempts (DRT-0073 on core pins of `ot_dsrom_su_hcpost_lane_pr`,
  `dsdv_gunit_l*f_bf`, `dsfd_coll_lane_*_ntf`, `qfd_dv_s*x_vmr`). It runs after placement and CTS, hours in.

**D. Cells added by the wire-length rule (MEASURED).**

| die | `OT_MAXWIRE_UM` | kits | cell growth at GRT, median (max) | buffers per cut net | families |
|---|---|---|---|---|---|
| QC | 33 | 8 | +66 % (69) | 3.0 | sle_stm, slw_stm |
| QC | 40-50 | 5 | +51-69 % | 2.5-3.4 | slw_fw |
| QC | 62-75 | 17 | +30-37 % (41) | 1.8-2.0 | fw, fe |
| S81 | 50 | 12 | +33 % (40) | 2.1 | slice_station |
| S81 | 100 | 67 | +16 % (28) | 1.5 | leaf, col_r2, serdes, eng |
| QC / HEAD / KV | 120 | 90+ | +4-5 % | 1.0-1.1 | all others |

slice_station t29: 46,080 nets cut, 97,397 buffers, 241,271 -> 338,668 cells. The tool itself warns (RSZ-0065:
"max wire length less than 143u increases wire delays"). RULEBOOK R-FLOW-3 already says 120 um kit-wide and that hold
no longer picks the relay pitch; the kits built on 11-14 still carry 33-75. The added cells land in the pin band and
the streets; 99 attempts then hit RSZ-0060 (buffer cap) in hold repair.

**E. Three DRCs from clean, one pin (MEASURED).**
QC slw_su_l0 (11 attempts) and sle_su_l0 (3) finish 57 detail-route iterations with exactly 3 violations, the same
three every time: "Rect Only" on M7, net `cland_tstart_in[0]`, at (158.14-158.22, 175.14-175.20). HEAD hd_spn_end
(2 attempts) ends the same way (3 x Rect Only M7). One type pin whose M7 access shape is not a rectangle.

**F. Steps with cost and no effect (MEASURED).**
- Antenna: 226 GRT logs report 0 net violations; 101 route logs carry GRT-0246 "no diode". ASAP7 has no antenna
  rule in this deck, so the step can only fail (FABLE-PD-HKQ K2 names one such failure on KV).
- DRT-0421 "term has no pins on routing grid" in 136 of 154 route logs (20-26 strap terms per kit): the source of the
  14 QC DRT-0206 stops (FABLE-PD-HKQ Q2).

## 2. Die level

### 2.1 Results as they landed tonight

| die | run | state at 22:45 PST | result |
|---|---|---|---|
| HEAD | DIE-HEAD-ROUTE-1 `head/p16` (epyc2) | done 22:13 | GRT 0 overflow, 50.89 m, 53,372 nets, use 0.33 % |
| HEAD | `head/p16r` (ot_clk tree) | clock DME running | - |
| KV | DIE-KV-ROUTE-1 `runs/p1` (epyc7) | GRT done; route stage dead | GRT 0 overflow, 286.5 m, 202,491 nets, use 2.47 %; then `PDN-0233` after 95 s |
| S81 | DIE-S81-GRT0 `s81/b3x2d` (epyc8) | clock DME, 59 of 98 regions after 35 min | - |
| QC | DIE-QC-GRT0 `qc/s3r` (epyc9) | dead since 22:09 | `FAIL_KIT: ModuleNotFoundError: No module named 'soft_reg_banks'` |

Two chains are dead and need their owners now:
- QC: the kit step cannot import `soft_reg_banks` (tool tree "tree3 + main" lacks the module). Nothing ran.
- KV: `pdngen` fails because the plan's PG regions include slivers 6.48 um wide or high (`ot_pg_1`, `ot_pg_4`,
  `ot_pg_9`, `ot_pg_11`); an M9 stripe is 12.96 um wide, so these grids are empty ("does not contain any shapes or
  vias") and OpenROAD stops. Merge each sliver into its neighbour region in the PG region generator.

### 2.2 What the 50.9 m is (MEASURED from `grt_st_TT/route_TT.guide`, per net class)

| die | class | nets | wire | mean per net | layers |
|---|---|---|---|---|---|
| HEAD | feed-through slot nets `ft_*` | 48,400 | 48.4 m | 1.00 mm (0.26-2.07) | M4-M7, 0.2 m on M8 |
| HEAD | clock tree `ck_*` | 1,801 nodes | 1.42 m | 0.79 mm | M8 0.66 m, M9 0.76 m |
| KV | feed-through slot nets | 170,209 | 277.1 m | 1.63 mm | M4-M7 139 m, M8 80 m, M9 58 m |
| KV | clock tree | 32,280 | 3.6 m | 0.11 mm | M8 1.9 m, M9 1.6 m |
| KV | reset | 1 | 0.18 m | - | - |

- `kit/grt/route.v` holds one net per feed-through bit, from the slot's `_i` pin to its `_o` pin on the same
  partition instance (for example `ft_sp#__hd`, 1,668 bits, 2,074 um each: the length of a spine strip).
- METHODOLOGY 12.1d puts feed-throughs inside the partition: stations, repeaters and wire are partition netlist, on
  the partition's own M4-M7, signed with the type. The type kits contain them (`u_ft_ft1_o_2` and the like).
- So the die GRT routes, a second time and without stations, wire that the types route themselves. It is an artefact
  of plan-shape abstracts (pins plus obstruction M1-M3 only). The run is still useful as a capacity check of the
  feed-through demand per type: it takes 1.2-1.3 % (HEAD) and 2.9-4.6 % (KV) of the quarter of M4-M7 the abstract
  leaves, so about 1 % of a type's M4-M7. Feed-through wire is not what fills the types.
- Real die-top signal wire: HEAD 228,108 seam bits on 468 ports, KV 602,002 seam bits, all pin-to-pin across the
  abutment (`abutted_pin_check` 0 bad bits on HEAD), `channel_ports` 0 on both. Length 0.

### 2.3 Die-top net budget

| net class | owner | layers | budget |
|---|---|---|---|
| seam signals | types (pins touch) | none | 0 um; any seam net with a gap is a plan error, not a route job |
| feed-throughs | types | type M4-M7 | 0 at die level; budget per type, checked in the type kit |
| clock | die | M8 / M9 | measured 1.4 m routed on HEAD (plan tree 4.7 m with tap stubs), 3.6 m on KV; plan 5 m per die |
| reset spine | die | M8 / M9 | one net per die, under 0.5 m |
| PG | die | M8 0.48 um at 4.32 (11 %), M9 12.96 um at 34.56-39.96 (32-37 %) | fixed by the plan |

Die M8/M9 after PG keeps about 89 % of M8 and 63-68 % of M9; the clock uses 0.03 % of each on HEAD. There is no
die-level routing shortage, and no reason to open more die layers or to move signals up.

### 2.4 Two things wrong in the die proof

- `head/p16` GRT prints M8 and M9 "reduction 0.00 %": the die PG is not in that model. Its "0 overflow" says nothing
  about clock against PG. The new `die_route.sh` runs `pdngen` first and derates M8/M9 by 0.4; only its result counts.
- `die_route.sh` then sends every non-abutted 2-pin net to detail route. That includes all feed-through nets
  (48,400 on HEAD, 170,209 on KV). Over plan-shape abstracts they route over open M4-M9 and prove nothing; over signed
  views they cross full obstructions and fail. On KV the global router already put 138 m of them on M8/M9, because
  the KV abstracts block 80 % of M7 (71.7 M tracks against 101 M on M5).
- Also not modelled: most S81, QC, KV and HEAD type kits have `MAX_ROUTING_LAYER = M8` (the M8 grant), against 12.1a
  "types never use M8". Measured type wire on M8: hd_st_str 0.59 m, hd_spn_wshim_tx 0.21 m, S81 leaf 0.09 m. The die
  abstracts carry no type M8 shapes, so die clock on M8 against type M8 wire is unchecked. INFERENCE: the grant rows
  keep them apart; the first die route on signed views must show it.

## 3. Routing architecture

| item | what we have | judgement |
|---|---|---|
| layer split | types M2-M7 (M8 by grant), die M8/M9 | right; keep. State the M8 grant in 12.1a so the die model can carry it |
| feed-throughs | inside the types, stations at 405 um | right; this is the industry form for abutted blocks |
| die-top signals | none, pins abut | right; the cleanest possible top level |
| PG | type M5/M6/M7 pairs, die M8/M9 | cost is acceptable (17-25 % of tracks) but the pairs run through the pin band and over cores unchanged |
| over-core routing | one layer per direction, derated twice | the weak point; industry blocks leave two layers per direction above a macro or route around it in sized channels |
| pin planning | pins on plan windows; legality found by detail route | wrong order; industry checks pin access when the floorplan is made |
| GRT overflow | fatal error | industry treats it as a metric and lets detail route decide, with a ceiling |
| wire-length rule | kit-wide 33-120 um | industry repairs by slew and capacitance; a length rule is for named nets |
| streets | R-STREET 43.2 um, 37.5 tracks per um | sound; col and leaf plans do not meet it yet (FABLE-PD-S81 levers 3 and 6) |

Tool use: 30 GRT iterations (15 is enough in the one kit measured), 64 detail-route iterations (fine), no per-layer
congestion map saved (the report is 2D, so "M6 26,063" cannot be located without a rerun), antenna step with no rule.

## 4. Levers, ranked by types unblocked

| # | lever | types | evidence | owner |
|---|---|---|---|---|
| 1 | Let small GRT remainders through to detail route; never relaunch the same failing net | S81 col_h9_r1 and h10_r1 bases (about 70 of 216 col types), KV hg / hgi 9, slice_station and leaf attempts | 1.2 A | KIT-OPS-5 (flow), KIT-WAVE-1 (relaunch rule) |
| 2 | Pin band: check pin access and PG clearance at floorplan, keep PG pairs and repeaters out of the band | every type that reaches route: S81 leaf 79 + station 47, HEAD 6, QC 17 seen, KV io / sys 4 | 1.2 C | PG-AWARE-1 + KIT-OPS-5 |
| 3 | Second horizontal layer above cores, and no blanket derate on the over-core layers | S81 col 216, QC cb family 12 | 1.2 B | DIE-S81-92 / S81-COL-STREET, QC die owner |
| 4 | Wire-length rule to 120 um kit-wide, as R-FLOW-3 already says | QC stm / fw / fe about 20, S81 slice_station 47 | 1.2 D | KIT-OPS-5, die owners (regenerate) |
| 5 | Move one pin: `cland_tstart_in[0]` | QC su_l0 (2 families, 14 attempts), HEAD hd_spn_end | 1.2 E | TYPE-QCCOLLN / QC-CORES-HEAD, HEAD-99 |
| 6 | Die proofs: fix the two dead chains, drop feed-through nets from die detail route, PG in every die GRT | 4 dies | 2.1, 2.4 | DIE-QC-GRT0, DIE-KV-ROUTE-1, DIE-HEAD-ROUTE-1 |

**Lever 1.** Root cause: a tool error is used as a gate that the owner's profile does not contain (blocking gates are
DRC 0 after route, setup, hold, bind). Fix: `-allow_congestion` on every kit GRT and on the incremental routes; the
kit goes on when the final 2D report has at most 0.1 % of gcells congested, else it is a design failure for the plan
owner. Cap the iterations at 15. In the wave, a kit that ended GRT-0116, GRT-0232 or DRT-0255 is relaunched only when
its inputs changed (key: kit hash plus failing net). Proof, one build: col_h9_r1 cl49d7a23e from its `4_cts.odb`
with the flag, to detail route. Pass: DRC 0 or a short list at the 4 gcells. If detail route fails at x 464-466,
y 1094, the fix is local: the M7 PG pair column over a core that is blocked to M6 leaves no vertical layer there, so
move the 5 nets' source registers `u_lpl_11_w` or drop that M7 pair over `bf_col3_c`.

**Lever 2.** Root cause: pins, the first register rank, the PG pairs and the repeaters of the wire rule all sit in
the first 80 um, and legality is first tested after 10 h. Fix: (a) run the pin-access step on the floorplan database
right after PDN (macros, pins and PG exist; minutes) and stop there on DRT-0073; (b) in the generator, every type pin
and every core pin on a face gets at least one track that is clear of the M5/M6/M7 pair rows by the track-truth rule,
or the pin moves one track; (c) PG-AWARE-1's pair-row keep-out for cells, on all four dies (`die_gen_env` s81 still
lacks it per FABLE-PD-S81 lever 5). Proof: slice_station t8 and hd_ctl_n, which fail on `ft2_i[688]` and
`w3u_i[427]` every time.

**Lever 3.** Root cause: cores were closed to M5 or M6 without asking what crosses them. Fix in this order:
(a) set the layer adjustment to 0 on M6 and M7 (and M8 where granted): these layers are 1-10 % used and the derate
only bites above cores; (b) col: give the col bases the M8 grant the leaf types have, so there are two horizontal
layers above M5 cores; (c) `bf_col3_c`: check whether its M6 obstruction is real metal; if it is a blanket, cut it to
the real shapes at the next core re-sign; (d) the street event of FABLE-PD-S81 lever 3 for what remains (col_r0 with
60,000-157,000). QC cb: the M8 grant on every cb kit (some cbn kits are still M7) and (a). Proof: plain GRT on one
col_r1 and one cbn placed database with (a) and (b); read the M6 line.

**Lever 4.** Root cause: a hold-driven repeater pitch became a kit-wide length rule. Fix: regenerate the QC relay and
S81 station kits at 120 um; where setup needs a shorter hop, put the rule on the named hop nets. Pass: growth at GRT
under 15 %.

**Lever 5.** Move the pin one M7 track or put it on M5 in the generator; rerun route only.

**Lever 6.** As in 2.1 and 2.4. The die GRT with feed-through nets stays as a demand check only, and is named so.

## 5. Stop list

- Stop reading die GRT wirelength as die-top wire, and do not size die M8/M9 or a die budget from it.
- Stop detail-routing feed-through nets at die level.
- Stop relaunching a kit whose last result was the same net in the same place (102 col_h9_r1 attempts, 4 hd_ctl_n).
- Stop treating "26,865" on col_h9_r1 as wall congestion before the one-build proof of lever 1. The re-floor is still
  right for col_r0.
- Stop kit-wide wire rules under 100 um.
- Stop the antenna step on ASAP7 kits.
- Stop GRT congestion iterations after 15.
- Do not open more layers, widen the die, or raise street widths on the evidence here: use is 4-10 %.

## 6. What I did not do

- No build. The lever 1 and lever 3 proofs are proposals with pass marks, not results.
- I did not locate the M6 overflow of col_r1 inside the type; the saved report is 2D.
- KV type data is thinner than the other dies (75 GRT logs, mostly hg / hgi, io and sys); KV ring and pc types are covered
  by FABLE-PD-HKQ, not here.
- S81 and QC die GRT had no result when I stopped; HEAD `p16r` neither.
