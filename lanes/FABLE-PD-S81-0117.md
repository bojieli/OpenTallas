# FABLE-PD-S81-0117: why the B6gE landing bands congest the S81 leaf kits (Event G y-slot / STRIP), and the fix

2026-11-16 PST. Fable PD review for COORD; cc DIE-S81-92, S81-LEAF-PLAN, S81-CA-BAND, S81-COL-CLK-IMPL, S81-PHYT1, FABLE-FIX-S81-COL.
Technical PD only. MEASURED = read by me from plans, kit files, congestion reports or my own runs. INFERENCE is marked.
Evidence dirs: epyc9 `/srv/opentallas-scratch2/claude/fable-pd-s81-0117/` (proof kits A_t68, B_t68, B_t65, ctl_t68; decks pgrt.tcl / pgrt.sh), intel2 `~/fable-pd-s81-0117/` (ot-run logs), my scripts epyc9 + epyc7 `/tmp/fable0117_*.py`. Read-only on the S81-LEAF-PLAN kits (epyc9 `s81-leaf-plan/evg/kit/*`); the proofs are copies.

## 0. Verdict

The cause is not the band rectangles as such. It is one lost plan key.

The CA band re-compose (`fallback_land.py compose ... --band-multi-rect`, run without `--band-ring ff`; first seen in the 11-15 14:33 composes B6gshcf / B6gslcf / B6gslsw, then in every composed plan after them) dropped `ring_place: "ff"` from all 988 ring bands that had it in B6gsl. B6gE, B6gF2a and B6gG3b carry it on 0 of 1,255 bands (MEASURED). Two things follow from that one key:

1. Kit side. Without the key the tag is `ring:<bus>` and not `ring:<bus>+ff`, so `landing_placement.tcl` places EVERY cell of the ring FIRM, first-fit in raw name order, and leaves nothing to global placement. On t65 `ft0_i` that is 27,866 FIRM cells (B6gsl form: flops only). The 14,565 unnamed logic cells are packed as one block at the band's low end (y 17..87), the storage flops follow in ASCII chunk order (dch 0, 10..17, 1, 2, ..) at y 87..250, and the upper half of the band (y 250..456) stays empty. 9,674 ring nets cross the cut at y 87 inside a band 38.7 um wide: 250 nets per um against about 47 V tracks per um. That is 5.3 times the supply, inside the band, on every wide ring.
2. Plan side. With ring "all" the composer reserves all cells at use 0.5: 8,105 / 0.5 um2 for a 1,104-bit ring, about 3.1 times the B6gsl band. A strip that size does not fit between the face and the first core, so the search slides the band along the face up to the reach limit. Bands now sit beside or past their own pin window (t65 `ft1_i`: pins y 247..487, band y 458..683; t68 `ft5_i`: pins x 336..461, band x 519..644).

The fix is to put the key back: one compose flag (`--band-ring ff`), or a post-compose key delta until the next compose. Reusing the B6gsl rects is not needed: with `+ff` and the kit's pin-slot mode the ring flops go to their own pins whatever the rect says (section 3, MEASURED on the proof kits).

The same defect is in every S81 family: 625 bands of 200 bits or more in 198 types, 459 bands of 512 bits or more in 174 types (section 4).

## 1. What is different between B6gsl and B6gE (question 1)

MEASURED, plans epyc7 `s81-b3-clk/ev/`:

| plan | bands | `ring_place: ff` | `rects_um` | `band_use_target` |
|---|---|---|---|---|
| B6gsh, B6gsl, B6gsl_or13_rp, B6gE_pre (not composed) | 1,199 | 988 (625 of them 200 bits or more) | 93 | none |
| B6gshcf, B6gslcf, B6gslsw (composed) | 1,253 | 0 | 0 | 0.5 on 1,236 |
| B6gslswrp, B6gE, B6gF2a, B6gG3b (composed) | 1,255 | 0 | 18-21 | 0.5 on 1,234-1,236 |

Compose command (MEASURED, `s81-b3-clk/chain_ca_e.sh` line 19): `fallback_land.py compose ... --band-multi-rect --band-order-type ... --band-use-type svc_hi_dsdv_svc_rs__t3=1.0`. No `--band-ring`; its default is `all` (`fallback_land.py` line 325). `--band-use-max` default 0.5.

Band geometry, the 13 y-slot types + t52 / t71 (MEASURED, my `bandcmp.py`; full table in the run output, examples here):

| type.bus | bits | B6gsl rect (w x h, area, hop) | B6gE rect (w x h, area, hop) | pin window |
|---|---|---|---|---|
| t65 ft0_i | 1,104 | 24 x 229, 5,437, 161 | 39 x 438, 17,048, 386 | E, y 7..246 |
| t65 ft1_i | 1,104 | 22 x 240, 5,183, 159 | 69 x 225, 15,527, 402 | E, y 247..487; band y 458..683 |
| t1 ft1_i | 1,104 | 22 x 240, 5,183, 159 | 71 x 240, 17,105, 280 | band moved 121 um inboard (x 1283..1354) |
| t61 ft1_i | 1,104 | 240 x 22, 5,183, 172 | 71 x 240, 17,105, 323 | N face; band turned 90 degrees |
| t68 / t24 ft5_i / ft4_i | 597 | 125 x 24, 2,964, 103 | 125 x 76, 9,432, 338 | S, x 336..461; band x 519..644 |
| t68 leafdn_i0 | 597 | 127 x 24, 3,010, 104 | 127 x 76, 9,577, 232 | S, x 614..740; band lifted to y 93..168, behind ft5_i's band |
| t56 ft9_i | 668 | 141 x 24, 3,338, 120 | 141 x 76, 10,622, 184 | |
| t32 ft3_i | 513 | 119 x 26, 2,855, 109 | 544 x 15, 8,230, 371 | |
| 70-bit buses | 70 | 17 x 41, 700, 67 | 17 x 93, 1,585, 119 | unchanged position |

Area ratio B6gE / B6gsl, all families (MEASURED): median 3.09 for 512-999 bits, 3.00 for 200-511, 2.05 for 1,000 or more, 2.26 below 200.

Why the size: `clock_landing_plan.ca_ring_reserve40_um2`. Ring "all": 5.36 W + 114 ceil(W/64) + 130 = 8,105 um2 at W 1,105. Ring "ff": (4 W + 72 ceil(W/64) + 73) x 0.729 = 4,220 um2. At use 0.5 that is 17,020 against 8,860 um2. The B6gsl bands were the flop reserve at use about 1.0 (5,155 in 5,183).

Kit placement (MEASURED from `ot_face_flops.txt` and `3_3_place_gp.log`):

| kit | plan bands | ring tag | FIRM ring cells | where |
|---|---|---|---|---|
| S81-LEAF-T14 form R, t14 `ft2_i` 668 bits (GRT 0, lane result) | B6gsl | `ring:ft2_i+ff` | 3,834 flops, bit-major, keyed to word bits | in the 147 x 24 strip over the pins; logic left to GPL |
| S81-LEAF-PLAN ys_t65 `ft0_i` 1,104 bits | B6gE | `ring:ft0_i` | 27,866 = all cells | logic block y 17..87, storage y 87..250 in ASCII chunk order, band y 250..456 empty |
| ys_t65, whole type | B6gE | | 68,983 FIRM cells | |
| ys_t68, whole type | B6gE | | 38,545 FIRM cells (9,635 with `+ff`, section 3) | |

Net measurement on ys_t65 `ft0_i` (MEASURED, `cut.py`: the kit's Yosys netlist of the ring module joined to the FIRM locations; 19,049 cells, 15,789 multi-pin nets):
- V span of a ring net: median 70 um, p90 176 um, max 222 um. A `d[i]` pin to its farthest load: median 104 um, p90 192 um.
- Sum of V spans 1.18 m in 9,022 um2 = 131 um of V wire per um2. H: 26.5.
- Nets crossing a horizontal cut of the 38.7-um band: y 47: 5,874; y 67: 8,700; y 87: 9,674 (250 per um); y 127: 7,026; y 167: 4,539; y 207: 2,307.
- V capacity in the same gcells (the kit's own congestion report): 26-27 tracks per 0.57 um gcell = 47 per um. Demand / supply at y 87 = 5.3.
- Example: `_14590_` is an AO21 fed by `d[186]`. It is the first cell placed, at the band corner (1386.72, 17.28). The pin of bit 186 is at y 205.6.

Congestion maps (MEASURED, `cong.py` on the 13 `congestion-15.rpt`; overflow inside a band rect / within 20 um of one):

| kit | total it15 | cland share | in band | within 20 um | worst band, overflow per um2 |
|---|---|---|---|---|---|
| t1 | 249,877 | 93 % | 73 % | 21 % | ft0_i 1,104 bits 6.39; ft1_i 4.24 |
| t23 | 213,144 | 91 % | 63 % | 22 % | ft0_i 7.13 |
| t65 | 231,401 | 94 % | 44 % | 25 % | ft0_i 3.35; ft1_i 2.89 |
| t67 | 217,379 | 88 % | 45 % | 23 % | ft0_i 3.04; ft1_i 2.54 |
| t61 | 126,601 | 90 % | 57 % | 20 % | ft1_i 3.82 |
| t56 | 87,138 | 87 % | 77 % | 18 % | ft9_i 668 bits 6.01 |
| t32 | 80,886 | 89 % | 20 % | 28 % | ft3_i 0.73 (544 x 15 strip) |
| t68 | 70,596 | 89 % | 81 % | 19 % | ft5_i 597 bits 4.81; leafdn_i0 1.22 |
| t24 cl2456157b | 69,941 | 89 % | 81 % | 18 % | ft4_i 4.81 |
| t62 | 50,291 | 42 % (ft 51 %) | 37 % | 12 % | ft4_i 1.17 |
| t38 | 47,537 | 87 % | 79 % | 15 % | ft0_i 597 bits 2.35 |
| t34 | 38,578 | 52 % (ft 38 %) | 41 % | 17 % | ft4_i 0.70 |
| t58 | 38,251 | 86 % | 60 % | 28 % | ft2_i 668 bits 2.16 |

By ring width, over all 13 kits: 70-bit and 1-2-bit bands 0.00 overflow per um2; 276-bit bands 0.00-0.70; 513-668-bit 0.14-6.0; 1,104-bit 2.5-7.1. That is why t10 / t74 (70-bit rings only) reach 0 on the same B6gE bands. H and V overflow inside a band are about equal, which fits a scrambled block and not a one-direction bundle.
Every hotspot the lane named sits at the logic-block / storage boundary of a wide ring, e.g. t65 (1400, 60) = `ft0_i` y 60..80.

The 15-iteration stop (owner rule since deleted): MEASURED series (`failfast_state.json`), iteration 5 / 10 / 15: t65 354,826 / 291,581 / 231,401; t1 320,903 / 279,102 / 249,877; t68 131,263 / 95,549 / 70,596; t58 118,508 / 41,974 / 38,251; t34 101,807 / 49,629 / 38,578. The decay from 10 to 15 is 9-26 % per 5 iterations. INFERENCE: at that rate none of the 13 reaches 0 by iteration 30 (best case t34 about 18,000, t58 about 27,000). The early stop did not create these failures, but the totals are not final values: do not rank the types by them.

Band position against ft bundles and core pins: the displaced bands also sit in front of other buses. t68: `ft5_i`'s band (x 519..644, y 17..93) covers the first 30 um of the `leafdn_i0` pin window (x 614..740), and `leafdn_i0`'s band was lifted to y 93..168 behind it. The t68 hotspot (560..600, 20..40) is inside that `ft5_i` band. This part disappears when the flops return to their pins (section 3).

## 2. Is this the col clock tap finding (FABLE-PD-S81-F2r / FABLE-FIX-S81-COL-SPECS)? Partly

- The routed col pilot of F2r (kw43-wave-1109n) predates the re-compose, so its 1,387 endpoints are not caused by this. Those specs stand as written.
- INFERENCE, to check on the next col pilot: col types carry 58 ring bands of 1,000 bits or more in 35 types and 72 narrow ones, all without the key in B6gE / B6gF2a. An all-cells FIRM ring adds its logic cells to the fixed area and puts ring flops (clock sinks) where the composer slid the band, not at the pins. FABLE-PD-S81-1045 item 1b measured 46 svc band rects more than 150 um from any tap. So the col tap-sink numbers of any pilot generated from B6gE or later are taken on the wrong ring placement. I did not read B6gF2r.json (epyc10).

## 3. Proof runs (question 2: reuse the B6gsl rects, a rule, or structural?)

Three private kit copies on epyc9 (copies of the lane's ys_t68 / ys_t65 kits, floorplan reused, `landing_placement.tcl` ring tags edited by hand, `OT_GRT_EARLY_STOP = 0`), run through ot-run with `run_kit.sh ... grt` (place, CTS, GRT, 30 iterations, no early stop):
- A_t68: B6gE rects, tags `+ff`.
- B_t68: B6gsl rects, tags `+ff`.
- B_t65: B6gsl rects, tags `+ff` / `+ffr` (two 1,104-bit E-face rings).
- ctl_t68: place-level GRT of the lane's unmodified ys_t68 `3_place.odb` (same deck as the place-level reads below).

Placement step (MEASURED, `3_3_place_gp.log` of the proofs):

| proof | FIRM cells in the type | ring lines |
|---|---|---|
| lane kit ys_t68 (control) | 38,545 | all ring cells FIRM |
| A_t68 and B_t68 | 9,635 | `ft5_i`: 3,516 ring flops next to their bit pin (S face strip 10.80 um deep, 105 columns over pin x 336.42..460.77), 11,670 logic cells left to global placement. Same line for `leafdn_i0`; `ft4_i` 1,671 flops / 5,570 logic cells |
| lane kit ys_t65 (control) | 68,983 | all ring cells FIRM |
| B_t65 | 16,375 | `ft0_i` and `ft1_i`: 6,461 ring flops each, bit-major, 21,405 logic cells each left to global placement |

A_t68 and B_t68 give the same pin strip for all three rings: with `+ff` and `OT_CLAND_PINSLOT = 1` (already in these kits) the flops are placed over their own pins, and the band rect is not used for N/S-face buses. So form A (B6gE rects kept) and form B (B6gsl rects) are the same placement on t68.

GRT, place level (`3_place.odb`, layers M2-M8, global adjustment 0 as in the kit, 30 congestion iterations, no early stop; deck `pgrt.tcl`):

| run | iteration 5 | end |
|---|---|---|
| ctl_t68: lane's ys_t68 placement, unchanged | 132,927 (H 86,973 / V 45,954). The lane's post-CTS kit read 131,263 at iteration 5, so the place-level read is the same measurement | 97,752 at iteration 10 (lane kit: 95,549); still running at iteration 12 of 30 when this was written, result in epyc9 `ctl_t68/grt.log` |
| A_t68: same kit, same B6gE rects, tags `+ff` | 60 | 0 overflow (H 0 / V 0), reached in 8 extra iterations, 576 s, usage 5.50 % |
| B_t65: B6gsl rects, `+ff` / `+ffr` | no report: finished before iteration 5 | 0 overflow (H 0 / V 0), reached in 2 extra iterations, 1,291 s, usage 9.13 %. Lane kit on the same rows: 354,826 at iteration 5, 231,401 at 15 |

Post-CTS, full kit flow of A_t68 (`run_kit.sh grt`, no early stop; MEASURED `failfast_state.json`): 116 at iteration 5, 1 at iteration 10, still running. Lane kit: 131,263 and 95,549.

The y-slot rows of Event G are in all of these kits. So on t68 and t65 (the worst of the 13, two 1,104-bit rings) the rows plus flops-only rings route to 0 at place level; the rows were never the problem.
Limits: B_t65 used the B6gsl rects, so form A (B6gE rects kept) is proven only for N/S-face rings (t68). E/W-face rings with B6gE rects and `+ff` were not run; lever 1 re-sizes those rects, lever 2 keeps them.
The three kit flows (place, CTS, GRT through `run_kit.sh`) continue on epyc9; their post-CTS totals will be in `<proof>/gen/<type>/run/reports/.../congestion-*.rpt` and intel2 `~/fable-pd-s81-0117/grt_<proof>.log`. S81-LEAF-PLAN can read them; I do not use them here.

Answer to question 2:
- Reusing the B6gsl rects is not the fix and is not needed. The key is. For N/S-face buses the rect does not even enter: A_t68 and B_t68 place the same flops on the same pin strip.
- A rule is needed so that this cannot come back silently (section 5, lever 3).
- Nothing structural (no outline, core or station change) is needed for the 11 band-dominated types.
- For E/W-face rings under lever 2 (key only, B6gE rects kept) run one kit (t65 form A) before the wave; under lever 1 the rects are re-sized and B_t65 is the proof.

## 4. Latent in other S81 types (count from the plan)

MEASURED on B6gE.json against B6gsl.json (`cnt.py`); B6gF2a and B6gG3b have the same 0 of 1,255. Ring bands without monitors:

| family | 1,000 bits or more | 512-999 | 200-511 | below 200 | types with a band of 512 or more |
|---|---|---|---|---|---|
| leaf | 33 | 105 | 65 | 106 | 55 |
| col | 58 | 0 | 0 | 72 | 35 |
| slice_station | 12 | 86 | 45 | 84 | 34 |
| dsdv_slice | 16 | 42 | 23 | 59 | 18 |
| svc | 31 | 29 | 13 | 33 | 16 |
| kv_leaf | 2 | 9 | 13 | 5 | 3 |
| other (bk_sel, eng, gunit, iqf, seqhost, serdes) | 1 | 35 | 7 | 4 | 13 |
| all | 153 | 306 | 166 | 363 | 174 |

- 625 bands of 200 bits or more in 198 types; 459 of 512 bits or more in 174 types. From the kit maps the failing class starts between 276 and 513 bits.
- Displacement (same comparison): 677 bands have a pin-to-band hop more than 50 um longer than in B6gsl; 296 bands do not overlap their B6gsl rect at all; 41 are at 395 um or more (reach limit 402.84).
- So every S81 kit generated from B6gslsw or later with a ring of about 500 bits or more is expected to fail GRT the same way (INFERENCE from 13 of 13 kits; the two 70-bit-only kits pass).

## 5. Ranked fix

| # | lever | evidence | owner |
|---|---|---|---|
| 1 | Compose command: add `--band-ring ff` to every `fallback_land.py compose` call of the S81 chain (`chain_ca_*.sh`, `bandtap_compose.sh`). This is the lever that holds: the `_pre` plans still carry the key (B6gE_pre: 988) and the compose step strips it, so a row applied before compose is lost again. Bands then size from the flop reserve (4,220 um2 per 1,104 bits by the formula, 8,860 at use 0.5 instead of 17,020) and fit over their pins. Accept: composed plan has `ring_place: ff` on all 988 ring bands (monitors excepted) and the kit log prints `OT_CLAND ring_place=ff` for each. Then run the existing `rehome_far_bands` (FACE_HOME + FACE_CROSSING, DIE-QC-97) for the bands still off their window | section 1 (key lost, 0 of 1,255; 677 bands displaced by more than 50 um), section 3 (t68: 132,927 -> 0), `clock_landing_plan.py` note DIE-HEAD-12 probe B (-97 % GRT overflow, flops-only against all-cells FIRM, hd_tile) | DIE-S81-92 (chain scripts and the next compose); S81-CA-BAND (compose tool, checks the flag with `--band-multi-rect`: `rects_um` bands take `+ff` but not `ff_rect_um` / `fill_axis`) |
| 2 | If no compose is due before the next kit wave: a post-compose plan delta that sets `ring_place = "ff"` on the same 988 bands (type + bus list from B6gE_pre.json), rects untouched. Same kit effect as the A_t68 proof (B6gE rects kept). The oversized rects stay as plan obstacles for taps and stations until lever 1 | section 3, form A | DIE-S81-92 composes the delta; S81-CA-BAND supplies the list |
| 3 | Guard, fail closed: (a) compose refuses to emit a band without `ring_place` when the input plan had `ff` on it (the carry-over line of DIE-QC-97 exists for resize, not for a fresh compose); (b) `kit_preflight` error when a ring of 200 bits or more has no `+ff` tag, with the count of FIRM cells | section 1: the loss was silent through 4 events | S81-CA-BAND for (a); S81-COL-CLK-IMPL for (b) with its col clock keys, since the col pilots need it first |
| 4 | t72: same key. `ft0_i` / `ft1_i` fail GPL because all 27,866 cells are reserved: 9,075.8 um2 against the band bound 6,046.3 (ratio 1.50). The flop reserve is 4,220 um2 x 1.05 = 4,431 by the composer's formula (0.73 of the bound); with the mapped count of B_t65 (6,461 flops x 0.729 x 1.05 = 4,946) it is 0.82. No rect or core change. With the compose flag of lever 1, the bands also get `ca_reserve40` fields again (today they have none: the compose fell back) | MEASURED error line (st_t72 `3_3_place_gp`), arithmetic from the composer's own formula | DIE-S81-92 (row), S81-LEAF-PLAN re-runs st_t72 |
| 5 | t62: its ft share is not a y-slot and not a band. 23,999 of 50,291 overflow is ft0 (9,163), ft1 (7,800), ft7 (5,629), all in x 300..600, y 0..100, more than 60 um from any ring band. There the two 1,104-bit E-W slots have stations at (360, 25) and (539, 25) in the S strip, across the `ft7_i` (598) and `ft4_o` (669) pin windows at x 336..610. It is the STRIP class on the S face. Give t62 a STRIP row: lift the ft1 station at (539, 25) back to its y 94 run (its neighbours are at (743, 94) and (180, 44)), keep only ft0 in the S strip, or widen the strip with `strip_widen.py`. Gate it together with lever 1 or 2 | MEASURED `ft.py` + `ft_stations.txt` + pins | S81-LEAF-PLAN (rows), DIE-S81-92 folds |
| 6 | t34: its ft share (13,511 of 38,578: ft5 4,408, ft2 2,968, ft3 1,725, ft4 1,564, ft1 1,490, ft0 1,356) is V overflow in the W strip x 0..100, y 0..400, i.e. the STRIP class the lane already built rows for (st_t34). The y-slot kit did not carry the STRIP rows and the STRIP kit did not carry the y-slot rows. Build ONE t34 kit with both row sets plus lever 1 or 2 | MEASURED `ft.py` | S81-LEAF-PLAN |
| 7 | After lever 1 or 2: re-run the same 13 y-slot kits + st t34 / t52 / t71 / t72 once, no early stop, and judge the y-slot rows on that run only | the present 19 runs say nothing about the rows | S81-LEAF-PLAN |

Order: 1 (or 2 if no compose is due) and 4 in the next delta, all families in one event; no tool change, kits regenerate. 3b before the next wave launch. 5 and 6 in parallel.

Cost of lever 1 / 2: the tag changes the kit of every type with a ring band, so those layout hashes change. Signed types re-sign (owner 11-12: re-sign is accepted).

Owner note (COORD, 11-16): FABLE-CLOSURE-0130 found the same missing key on all S81 bands, and FABLE-FIX-S81-RINGS now owns the implementation of levers 1-3. The owners in the table name who supplies what to that lane.

## 6. Stop list

- Re-running or re-ranking leaf kits on B6gE / B6gF2 / B6gG3 bands as they are. 13 of 13 fail for a reason the rows cannot change.
- Reusing or hand-copying B6gsl rects into B6gE types (question 2). Not needed; the B6gsl rects overlap the present band set (t68 `leafdn_i0` on `ft5_i`, t65 `ft1_i` on `ft0_i`, `ft6_i` / `ft7_i`).
- Growing bands or lowering `band_use_max` to relieve "band density". The bands are already 3 times too large; half of each wide band is empty.
- Reading the 38k-250k totals as a ranking of the y-slot rows, or as final values (stopped at iteration 15).
- More y-slot density work (below 7.7 flops per um) on the 11 band-dominated types before the re-run of lever 7.
- M9 grant, outline growth or core moves as an answer to these 13 kits.
- Tap or sink-count conclusions on any col / svc / slice_station pilot generated from B6gslsw or later, until its rings are `+ff`.
- A t72 band re-site or core push to gain band area.

## 7. Not checked

- B6gF2r.json (epyc10) was not read; B6gF2a and B6gG3b were.
- The three STRIP kits t34 / t52 / t71 (their congestion reports are not on epyc9); the lane's 82-88 % split is taken as given.
- Whether any consumer other than `landing_place.py` reads `ring_place` (G0, bind, LATCHECK). The key was in B6gsl through bind and LATCHECK, so I expect none.
- Timing after the change. The flops return to the pins, so pin-to-ring hops shorten, but no STA was run.
- The t62 station move is geometry only; the y of the free run was not screened against cores.
- The proofs edit `landing_placement.tcl` by hand. A kit generated from a plan with the key must show the same `OT_CLAND ring_place=ff` lines; that is the accept test for lever 1.
