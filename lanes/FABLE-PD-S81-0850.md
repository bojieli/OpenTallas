# FABLE-PD-S81-0850: S81 plan event B6gslsw / B6gslswrp, queued deltas, svc tap sites (2026-11-15 08:57 PST)

Read-only. MEASURED = logs, plans and sidecars on epyc7 `s81-b3-clk` (my scripts `/tmp/fable0850_*.py`). INFERENCE marked.
State at 08:55: B6gslsw G0 done (176 errors, 0 new against B6gsl, 70 clock_landings gone), elab running. B6gslswrp compose done, G0 running (about 50 min behind). No bind or LATCHECK result exists yet for either.

## 1. The 17 placement failures
- All 17 are one class: "no macro-free clock landing storage band" (single-rect search). 12 on 7 svc types (svc_hi rs t1-t6, pvso_entry t2, svc_lo rs t7), 4 on leaf t8 / t72 (ft0_i, ft1_i), 1 on slice_station t51 (2-bit monitor_0 ring).
- Not caused by the strap window: the same 17 are in B6gslcf, B6gshcf and TYM1-3; the class dates from 11-01 (DIE-S81-47).
- They do not touch G0, bind or LATCHECK. They block the kits: `landing_place.band_rects` raises "landing band absent", so those 11 types cannot generate.
- B6gslswrp compose: **0 failures** (1,255 bands, 18 multi-rect). Form J clears 16 (TYM3J, form J without the row, leaves only t51). The re-parent row clears t51: its monitor band no longer exists. Lane sums equal B6gslsw (clock_landing 2,522, cycles 13,551, minimum 1); reset release 136 and boot 757 unchanged.

## 2. Structural risks
| # | item | number | consequence | owner |
|---|---|---|---|---|
| a | Form J bands at the reach limit | 15 of the 16 re-placed bands have pin-to-band hop 401.9-402.8 um (limit 402.84); 2 to 9 rects, smallest side 2.16 um (8 rows) on 4 bands | no slack for a detour in an 11-15 um macro channel; type P&R decides | S81-CA-BAND: GPL + CTS pilot on svc_hi t6 (9 rects) and t3 before the svc wave |
| b | CA strap window | sim margin 105.5 / 106.0 ps against the 100 gate, nominal policy; arrivals are the B6gsh GRT-RC die clock; unshared path up to 11,165 ps | 5.5 ps to the gate: any die clock re-route needs the table re-planned (minutes) before die STA; under the AOCV corners 967 of 993 crossings would need deeper rings (not gating, 12.24b) | DIE-S81-92 |
| c | Tool tree | B6gslswrp composes with `s81-ca-band/tools`, B6gslsw with `ca_tools`; most of `die_plan/*.py` differs; branch c9d15309 is MERGE-FAIL (2 tests) | the winner must be reproducible from one merged tree | S81-CA-BAND, MERGE-QUEUE |
| d | E2 built on a composed plan | E2 = rows on B6gslcf (old table, 7 lanes at -1). Bands were not re-placed: t68 ft5_i and t24 cl2456157b ft4_i lie 1,035 um2 on the moved ve_m core and 1,408 um2 on stations | E2.json cannot be adopted or bound as is | S81-LEAF-PLAN |
| e | E2 latency | 59 lanes, +120 cycles in total (not 2 stations); 4 slice_station outlines grow to 1,650 / 1,754 um | LATCHECK prices it; pre-approved | S81-LEAF-PLAN |

Reset and clock landing: no new class in either candidate (landing contract 0 errors, start tree 233 uses, 0 open).

## 3. Stacking the four deltas
They stack in one bind only as rows on the pre-compose plan, with one compose last. Conflicts measured:
- TYM3 R4 and tr4 edit the same rows: 24 col types, 132 half `.ck` taps moved by R4 are among the 1,728 rows tr4 deletes (22 -> 14 taps per type). Apply tr4, then re-run R4.
- TYM3 as built lacks or13 (13 leaf hard_cores) and uses the old table: proof only.
- TYM3 keep_outs (7 -> 165, reset tree of col types) and E2 (83 types: 43 leaf, 8 station, 12 col_h10_r0 taps only) share no key. PHYT1 touches phy__t1 only.

Order: (1) adopt the winner; (2) one event on `B6gsl_or13_rp`: tr4 + idx overlay -> PHYT1 row -> TYM3 keep_outs, R2, R4 re-run -> E2 rows via rows_merge -> compose (ca_swm, form J, chain_ca_band93 guards) -> superset -> G0, bind, LATCHECK, bind_reset diff. (3) svc tap rows of section 5 in the same pre-compose step.

## 4. Stop list
1. B6gshcfrp, TYM3, TYM3J binds (TYM1 and TYM2 already failed): old table gives 7 lanes at -1, and their chains lack the flag restore, so bind ends on the bk_sel__t2 EMIT error (80 errors in TYM1). About 10 GB of elab each. The compose results are the evidence already used above.
2. Any further build on B6gslcf / B6gshcf, including E2 G0 copies with clamped lanes.
3. Row patches on a composed plan (E2 form, TYM2 superset: bind fails on added tap clk_t40 halo).
4. Do not stop TRIDX (B6gslsw sidecar, valid) or the B6gslsw / B6gslswrp chains.
5. If B6gslsw wins the race, adopt it for the 324 unaffected types and take B6gslswrp as the next delta at once; do not release the 11 band-less types from B6gslsw.

## 5. Ruling: svc types with no legal tap site (COORD question)
MEASURED on B6gslsw, 8 types: macros cover 70-73 % of the outline (117 or 138 boxes); no sink is inside a macro box. Channel widths (t3): x 11.0-15.1 um on 98 of 105 gaps, y 10.8-17.28 um. `TAP_CLEAR_UM` is 8.64 per side, so a channel under 17.28 um holds no legal tap. Sinks farther than 200 um from a legal site: hi t1 11,720 of 38,984 (max 624 um), t3 393, t4 393, t5 4,014, t6 497, lo t1 7,780, lo t7 1,734, lo_w t1 2,570.
With clear 4.32 um (my grid model): 0 sinks beyond 200 um, worst 26.3 um. `taps.density_taps` re-run in memory at 4.32: t3 36 taps, max load 1,047, max distance 96.9 um; t1 97 taps, 938, 99.3 um (radius 100).
Ruling: **halo change plus reservation**. Add a per-type `clock.tap_clear_um` (4.32, = CORE_MARGIN) for the 8 svc types; the density taps then land in the channels as explicit rows. Not a macro-local leaf: the uncovered sinks are channel std cells, not macro pins. Reserve the tap sites before compose and make them band obstacles (`_band_obstacles` ignores taps in padded mode), because form J puts ring bands in the same channels. Owners: S81-PHYT1 (key + rows), S81-CA-BAND (obstacle), DIE-S81-92 (event).

## Not verified
Bind and LATCHECK of either candidate; the 4.32 clear against PG / pin-track snap in an 11 um channel (2.4 um legal strip); band use against the mapped ring footprint for t3 (0.88 um2 per storage flop).
