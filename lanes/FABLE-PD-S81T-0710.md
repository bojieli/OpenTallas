# FABLE-PD-S81T-0710 2026-11-15 07:10 PST (COORD additions 07:40): S81 type failures t47, t75, leaf t14, col_h10_r1, phy__t1 (t37 dropped: signed off)

Scope: technical PD, type level. Read-only: nothing launched, stopped or changed. Plans read on epyc7
`/srv/opentallas-scratch2/claude/s81-b3-clk/ev/` (B3t = wave plan 7073a6b4a59, B6gsl = plan of record, B6gslcf = CA delta in bind).
MEASURED = read from a log, report, plan or render today. ESTIMATE = computed from plan geometry, not built.

## 0. Verdicts

| type | real state | root cause | level | owner | in the B6gsl/CA delta? |
|---|---|---|---|---|---|
| slice_station__t47 | routed, DRC 0, DRV 0, TT +86.09; FF hold -0.54 ps on 1 endpoint | hold ECO at zero margin oscillates between two neighbour output bits; stop rule ends it | type (ECO setting) | new lane (one ECO job) | no for the ECO; the CA delta changes t47, so the setting must go into the release recipe |
| slice_station__t37 | signed off 11-15 (form c); dropped | S-face landing bands; see section 2 | - | - | rebuild on the CA delta with the form c recipe |
| col_h10_r1 (12 types) | all forms end in timing repair: hold -329 to -347 ps on about 13,000 endpoints, setup -217 to -223 on about 3,200 | tap trees 218-519 ps against 250, plus the plan tap window; not routable-by-recipe | plan (clock) | DIE-S81-92 | two of the three plan fixes are in B6gslcf; the col tap window and reset copies are not |
| phy__t1 | never reached a design result: job 1 infra exit 1, rerun cancelled. 1.21M is an estimator error; real count 101,755 | census measures macro pins at the macro origin. Real blocker ahead: one clock tap for 19,922 flops, 3,987 ps insertion | flow fix, then plan (clock taps). No split | new lane (census fix) + DIE-S81-92 (taps) | taps: yes, phy__t1 has none in B6gslcf |
| ot_s81sl_leaf__t75 | design failure. The INFRA label is only the last job's end (SIGTERM from outside after 9.5 h) | five feed-throughs (3,634 bits) run around the SW core cluster through a 43.2-um W strip: 2.4 x its tracks | plan | S81-LEAF-PLAN | yes, as a t75 row change; LT2 did not fix it |
| ot_s81sl_leaf__t14 | not closed. Throat fix works (5,751 -> 139) but GRT still does not converge | residual is the 8.64-um ve_s / ve_m slot (ft0 last station + ft2), plus 1,483 station sites that lie inside macros | plan | S81-LEAF-PLAN (TL-LEAFT14 runs the proof) | yes, as a t14 row change on top of B6gslcf |

The first four are landed types: B6gslcf changes their landing bands and adds count straps (t47 14 diffs, t37 34, t75 31, t14 29 against
B6gsl). Every one is rebuilt when the CA delta is adopted, so each fix below is written to land in that delta or in its release recipe.

## 1. slice_station__t47: "timing after route"

MEASURED (epyc2 `/srv/opentallas-scratch3/claude/kw24-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/slice_station__t47/attempt_20/gen/slice_station__t47`,
`autopilot_chain_*.json`, `eco_20261107_100723_2197933/i{1,2,3}/signoff`):
- Block 706eea380878, 46,788 cells. It is the latest attempt (11-07) and the block is unchanged through B6gsl (not in DIE-S81-92-delta.tsv).
- Base route: TT +109.21, FF hold -42.16 on 1,442 endpoints, 412 slew violations, DRC 0.
- Late ECO: i1 FF -2.85, i2 -0.54, i3 -4.09; TT +86.09, DRV 0, DRC 0 in all three. One violating endpoint each time.
- The endpoint is an output port: i2 `ft0_o[70]`, i3 `ft0_o[71]`, from `u_ft_ft0_o_5/q[..]` (last ft0 station) against the IO clock vclk.
  Launch clock arrives at 124.17 ps (tap clk_t17, source latency -75), vclk reference 195.80 + 12.5 inter-clock uncertainty = 208.30
  required, data arrives 207.76. The path is flop + INVx3 + BUFx2.
- The loop ran with `hold_margin_ps 0` and stopped on "WNS gain < 1.0 ps". Each pass fixes one bit to about zero and re-routes; the
  neighbour bit then lands a few ps short.

Root cause: not a structure problem. The 1,442 -> 1 repair worked; the last endpoint moves by +-4 ps between passes because the repair
target is exactly 0.
Fix (ranked):
1. One more ECO pass on the i2 database with a 5 ps hold target (`hold_margin_ps 5`). Cost about 3.2 h, one job (i2 took 11,365 s).
   ESTIMATE: closes, the spread over three passes is 3.6 ps and TT has 86 ps of room. Not run.
2. Same setting in the release recipe for the slice_station family (KIT-OPS-5), and exempt "violators <= 5" from the 1-ps stop rule.
3. For the CA rebuild use the pre-GRT FF hold build (TYPE-SLICE-HOLD recipe) so the port padding is in before routing. Not measured by me.
Class: 1 type in the "timing after route" class today (failure_breakdown). 25 S81 types have a routed-not-signed row since 11-06
(19 slice_station); I did not open the others.
Stop: no full rebuild of t47 on the B6gsl block, and no fourth zero-margin ECO pass.

## 2. slice_station__t37: dropped (signed off)

Signed off 11-15 by private form c (epyc8 `/srv/opentallas-scratch2/claude/typeslicet37/c`, density 0.35, M9, allow-congestion; TT +5.81,
DRC 0; FF hold raw -7.99 on 794 endpoints, all from input ports, left to the die check). Archived by TYPES-S81-FAIL-1115. Two facts
worth keeping for the rebuild on the CA delta (its landing contract changes there):
- The wave kit's 165 overflow was all at the S landing face (ft13_i / ft14_i rings, bands 109 x 25.9 and 43 x 50 um). B6gslcf makes
  them 75.6 x 109 and 108 x 78 um, so the cause is removed in the plan; form c is the fallback recipe.
- The edge-mode kit died on DRT-0255 with all four access points inside the M6 PG pair row y 135.744..136.416: the known pair-row
  class, 10 slice_station and 9 leaf types since 11-13. PG-AWARE-1 has no route-level proof yet.

## 3. ot_s81sl_leaf__t75: FAIL route INFRA

MEASURED:
- Job 515aa52f31fc (intel2 `~/coord/autopilot/jobs/515aa52f31fc/a1.log`): admitted after 4,929 s, preflight PASS, then
  "ot-job: signal 15 ... exit 143" and exit 137 at 19:13 PST. An outside stop, no host memory kill in the log. The sealed job
  directory is deleted, so what stage it was in is not recoverable. INFRA is correct for that one job only.
- Same kit's placed database, GRT by FABLE-REVIEW-CONG (epyc8 `/srv/opentallas-scratch/claude/fable-review-cong/d/t75`): base
  `Total ... 14.55% 59 / 37 / 1204815`; with the 11-14 fix form 476,498 left after 15 iterations.
- Base overflow map (`base_congestion.rpt`): S strip y 0..60, x 60..360 horizontal (capacity 18-19 per gcell) and W strip x 0..60
  vertical (capacity 20), plus the first rows over ve_m (capacity 5.5).
- B6gslcf row (LT2 form): ve_m [43.2, 52.4]-[216, 398], ve_s [224.6, 34.6]-[397.4, 380.2], vsw [60.5, 414.7]-[285.1, 639.4].
  Stations in the W strip: ft1 (1104, last station x 11..24), ft2 (668), ft3 (668), ft4 (597), ft5 (597). ft3 enters at x 283..429
  on N, goes to the W strip, down, and back east along the S strip to its S pins at x 283..429. ft5 enters at S x 430..557, goes west
  to x 15..37, up the W strip, then east through the 16.7-um gap between ve_m and vsw.

Root cause: the SW cluster sits in the corner where six feed-throughs enter and leave, and the station path sends five of them around
it. ESTIMATE: W strip 43.2 um = 76 gcells x 20 = about 1,500 vertical tracks against 3,634 bits = 2.4 x. S strip under ve_s 34.56 um
= about 1,150 horizontal tracks against ft0 + ft1 + ft3 + ft5 = 3,473 bits = 3 x. LT2 moved ve_m 17.8 um north and re-banded the
stations; the path is the same, so t75 fails again on B6gsl and B6gslcf.
Fix (ranked, plan):
1. Re-path ft3, ft4, ft5 straight: ft5 north through the open column x 476..557 east of ve_s (only vq, 130 um, in the way); ft3 and
   ft4 over ve_s / ve_m with stations in the S strip, the 380..415 gap and above vsw (hops 346 and 225 um, under 405). That leaves
   ft1 + ft2 = 1,772 bits in the W strip.
2. Then shift the cluster so the W strip is at least 60.5 um (1,772 bits = 0.83) or 86.4 um (0.58). The block shift of
   FABLE-LEAF-FTSLOT alone is not enough: 86.4 um holds about 3,030 tracks against 3,634 bits.
3. Proof before any wave launch: place + GRT only, 0 overflow inside 30 iterations.
Class (ESTIMATE, same screen on all 80 leaf types of B6gslcf, stations inside a core-to-face strip, bits over tracks): 13 types over
1.0: t28 2.95, t75 2.40, t34 1.95, t71 1.73, t13 1.67, t8 1.53, t72 1.53, t43 1.27, t47 1.27, t52 1.20, t33 1.16, t10 1.04, t74 1.04.
The top five are exactly the FABLE-LEAF-FTSLOT list. 8 more are between 0.6 and 1.0.
Stop: no retry key for t75 as INFRA; no wave launch of the 13 on their current rows. The S81-LEAF-PLAN proof on epyc9
`s81-leaf-plan/k/t75/proof` (B4L-era kit, GRT at extra iteration 30/30, started 11-14) cannot inform the B6 row: owner lane cancels.

## 4. leaf t14: GRT overflow

What was tried since FABLE-TRIAGE-S81 section 8 (TL-LEAFT14 r2, epyc10 `/srv/opentallas-scratch2/claude/tl-leaft14/r2/ot_s81sl_leaf__t14`):
u_vs moved +34.56 um in `macro_place.tcl`, ft5 last station changed in `ft_stations.txt`. Place + CTS done 10:29 UTC, GRT since then.

MEASURED:
- Not closed. GRT is in its fifth pass after 4.2 h (four GRT-0273 NDR drops). Overflow by report: pass at iteration 5 22,206,
  iteration 10 571, iteration 15 139 (r1: 5,751 at iteration 20). The throat is gone from the map.
- The 139: 77 vertical at the N face x 160..240, y above 1200 (`u_cland_ft2_i` ring cells) and in the ve_s / ve_m slot at y 40..100;
  62 horizontal at x 200..240, y 100..280 (capacity 6.6-7.6 = M8 at the macro edges). Nets: `u_ft_ft0_o_5` 539 mentions,
  `u_ft_ft2_o_4` 256, `u_ft_ft4_o_1` 131.
- r2 did not test the station move: the kit places from `ft_bit_sites.tcl`, which was not edited. ft5 stage 3 still sits at
  x 209.5..280.8, y 248..489, and 211 of its sites are now under the moved u_vs.
- Station sites inside macros in the kit (`ft_bit_sites.tcl` against the macro boxes; boxes confirmed on `layout_review/place/layout.png`):
  ft2 stage 2 all 669 inside u_vsw, ft4 stage 4 299 in u_vsw, ft3 stage 3 74 in u_vsw, ft0 stage 3 233 in vn_b, ft5 stage 1 238 in
  vn_b. The legaliser reports max displacement 126 um. The B6gslcf row still has them (669 / 289 / 64 / 233 / 228 by site origin).
  G0 reports only the ft5 one as new; the rest sit in the accepted baseline.
- B6gslcf row: u_vs at y 440.64 (LT2), ft5 last station at x 125..168, y 419..433. ft0 stage 5 still has 904 sites in the 8.64-um
  slot and ft2 stage 5 214; ft2 (668 bits, N to S) passes through the slot.

Root cause of what is left: (a) the 8.64-um slot between ve_s and ve_m carries the ft0 last station (1104 bits turning west over
ve_s on M8) and the ft2 column; 15 gcells x 23.6 = about 354 vertical tracks against 668 for ft2 alone. (b) 1,483 station flops
have plan sites inside macros and are pushed to the macro edges. Same family as the throat: cores too close to each other.
Fix (ranked, plan, one t14 row):
1. Keep u_vs +34.56 (measured: 5,751 -> 139).
2. Open the slot: ve_m east by 34.56 um (x 216.0 -> 250.56; free up to vn_b at 596). Slot 43.2 um = about 1,790 vertical tracks,
   ft2 = 0.37, and the ft0 last station fits beside it. ESTIMATE.
3. Re-site the five station stages that lie in u_vsw and vn_b (ft2 stage 2 north of u_vsw at y 900..930; ft0 stage 3 and ft5 stage 1
   west of x 596). Regenerate `ft_bit_sites` with the ft_throat_fix tool; do not hand-edit `ft_stations.txt`.
4. N-face ring: B6gslcf gives ft2_i a 145 x 73 um band; check it in the same proof.
Pass = place + GRT 0 overflow inside 30 iterations on the regenerated kit (src_rel2 gen passes for t14 since 06:19).
Class (MEASURED on B6gslcf): station sites inside macros in 5 leaf types (t14, t32, t65, t16, t38); a slot under 20 um holding more
than 200 station sites in 5 (t58 1,342, t14 1,132, t68 403, t24 cl2456157b 403, t65 263).
Stop: r2 is the same residual every pass; owner lane cancels it. No t14 launch on the B3t kit, the B6gsl row or the B6gslcf row.

## 5. col_h10_r1 (COORD addition a): forms stuck in timing repair

Already diagnosed in FABLE-PD-S81-2250 section 1 (fa / fd). New here: the two later forms and what the CA plan carries.

MEASURED:
- "About -330" is hold, not setup. fa / fd (22:2x 11-14): hold -328.49 on 12,263 endpoints, setup -222.8 on 3,375.
  fc (epyc8 `/srv/opentallas-scratch2/claude/type-colh10r1/fc`, density 0.4, M8, max wire 200 / 220, `5_1_grt.tmp.log`):
  setup repair ran 8,047 s and ended -216.607 on 3,017 endpoints (RSZ-0062), worst endpoint `u_u_e8_u_w/go_tag[1]`; start-point TNS
  -7,616 against end-point TNS -145,815. Hold then started at -432.48 on 13,066 endpoints, reached -346.67 with 569 delay cells
  (RSZ-0060, buffer cap) in 8,132 s. The log ends in GRT-0116. fb (density 0.4 only) also ended GRT-0116.
- So four recipes (density, top layer, max wire, congestion allowance) gave the same timing picture, as section 1.3 of 2250 predicted.
- Plan, 12 col_h10_r1 types: B3t has 20 grid taps, no `tap_max_sinks`, no `tap_group`. B6gslcf has 28 taps, `tap_max_sinks` 1500,
  `tap_pitch_um` 208, `insertion_ps` 450 and a `tap_group` for `u_lpad_*`. All 216 col types have `tap_max_sinks` 1500.
  `tap_window` is still absent on all 216 col types. No `reset_replicate` on col_h10_r1.
- Kit: core tap `clk_c4` for `u_e8_u_w` is written as 250 against a core depth of 532.99 (`core_taps.txt`).

Root cause: clock, three parts (2250 section 1.2, MEASURED there on 12,948 hold endpoints).
A. Grid-tap trees at 218-519 ps mean against 250, taps at the 3,000-sink cap: 5,667 endpoints, worst pair clk_t1 262 / clk_t6 597.
B. Plan tap window 179-208 ps early on every grid tap with no credit between taps: 7,281 endpoints exist only because of it.
C. Port hold on `frame_int_i1`: 1,648 endpoints.
Setup: the end-point TNS is 19 times the start-point TNS, so a few sources fan out to about 3,200 endpoints. INFERENCE: the reset
register (first worst endpoint is a RESETN pin, -243) and the `go_tag` broadcast into the element halves, whose tap is capped at
250 against 533 of real depth. I did not pull the path report.

Fix (ranked; owner DIE-S81-92):
1. A is in B6gslcf (1500 sinks, pitch 208, 450 budget, lpad tap group). Build one col_h10_r1 to CTS on it before anything else.
   Pass (from 2250): tap mean spread under 80 ps, FF hold before repair under 1,500 endpoints and above -120 ps.
2. B is not in the delta: add the col tap window. One flat 165 ps on every col grid tap first (FABLE-TRIAGE-S81 1.1), per-port
   values after the die clock rerun. Without it about half of the hold endpoints come back on every col type (216 types).
3. Setup: `reset_replicate` on col_h10_r1 as on col_h9_r2, and the element-half tap at the midpoint instead of the 250 cap
   (2250 section 2 row 2: 8 % setup TNS on the fa database). Measure setup on the CTS build of item 1; if `go_tag` is still over
   -100 ps it needs one register stage at the half boundary, which is an RTL item, not PD.
4. C: `clock.seam_hold` 60-90 ps (KIT-OPS-5 ask), after 1 and 2.
Level: plan. Class: 12 col_h10_r1 types directly; cause B is on all 216 col types.
Stop: no further col_h10_r1 form on the B3t block with any recipe; no hold padding run above 1,500 endpoints.

## 6. phy__t1 (COORD addition b): split or flow fix

Ruling: flow fix. No split. The type is not large, and it has not yet produced a design result.

MEASURED:
- Job 446ace226c80 (intel2 `~/coord/autopilot/jobs/446ace226c80/a1.log`): the sealed run went to intel2 and died in `ot-job` with
  `FileNotFoundError: /home/ubuntu/.local/bin/ot-job-docker` (exit 1; the file is missing on intel2 and on intel1). The unsealed
  rerun on epyc2 was killed by signal 15 from a lane's cancel loop over held items (AP_RC 143). No GRT or route step ran.
  "Exit 1 after CTS" is the infra error; the CTS log is from the wave's own place stage.
- Size (intel1 `.../items/phy__t1/attempt_10/gen/phy__t1/run/logs/.../4_1_cts.log`, `2_1_floorplan.log`): outline 8657.28 x 1226.88,
  one macro (`ot_hbm3e_phy_v41x...`) of 10.01 mm2 in a 10.54 mm2 core. Standard cells: 39,861 after synthesis, 101,755 non-tap
  after CTS, movable area 17,005 um2. Legalised HPWL 5.69 m.
- The 1,207,189 is 101,755 + `maxwire_est` 1,105,434. `cell_census.tcl` takes each pin at `[$inst getLocation]`, the instance
  origin. For a pin of the 8.4-mm macro that is the macro's corner, so every net that touches the macro is measured from that corner.
  Check: at the floorplan stage only nets between the macro and ports are measured (19,915 nets) and they give +484,110 = 24
  repeaters = 2.4 mm each. With 5.69 m of real HPWL at 100 um the bound is about 57,000 repeaters, so about 160,000 cells.
- Clock at CTS: one tap `clk`, 19,922 register sinks, tap insertion 3,987 ps mean (3,663-6,641) against 250; tool note "re-pitch
  taps to <= 27 um"; clock leaf repeat worst load distance 1,765 -> 883 um; reset max hop 5,549 um.
- Plan: phy__t1 has no `clock.taps`, no `tap_max_sinks` and no hard_cores row in B3t and in B6gslcf.

Root cause: (1) infra: sealed jobs sent to a host without `ot-job-docker`. (2) the census error above. (3) Real and still ahead:
a 40,000-cell wrapper strung along an 8.66-mm macro on one clock tap. 4 to 6.6 ns of insertion cannot meet 833 ps at any size.
Fix (ranked):
1. Census: use the pin position (`[$it getBBox]` centre, or `getAvgXY`) for macro pins. One-proc change in
   `tools/die_plan/cell_census.tcl`. Any type with a large macro is over-counted today; the error is at most (macro size / 100) per net.
2. Infra: install `ot-job-docker` on intel2 / intel1 or keep sealed route jobs off hosts without it (KIT-OPS-5).
3. Plan (DIE-S81-92, in the CA delta or the next one): grid taps for phy__t1 along the strip. 19,922 sinks at 1,500 per tap is
   14 taps or more, at the 208-um pitch along 8.66 mm about 42; flops grouped per tap by x. Reset by the same segments.
4. Then one build to CTS; judge on tap mean spread and insertion, as for col.
Split form, if it is ever wanted: not by cell count. The only sound split is along x by PHY lane group, with the macro kept whole as
a parent-level core and the wrapper cut into strips that each own their face flops and one tap group. Not recommended: item 3
gives the same locality without new types or seams.
Class: 1 type (phy__t1). The census error touches every type with a macro; material only where a macro is millimetres wide.
Stop: no split work, no >400k handling for phy__t1, no relaunch before it has taps.

## 7. Stop list

- t14: cancel r2 (TL-LEAFT14). No relaunch until the row change of section 4 passes place + GRT.
- t75: no retry as INFRA; no launch on the B6gsl / B6gslcf row. Cancel the B4L-era proof on epyc9 (S81-LEAF-PLAN).
- t37: signed off; nothing more on B3t.
- col_h10_r1: no form on the B3t block. phy__t1: no split, no relaunch before it has clock taps.
- t47: no full rebuild and no zero-margin ECO pass.
- The 13 leaf types of section 3 and the 5 + 5 of section 4: hold at release of the CA delta until their rows are re-pathed.

## 8. Not verified

- No what-if was run. Every "fix" number is an estimate from plan geometry and the measured gcell capacities (20-24 per gcell in
  open rows, 5.5 vertical and 6.6-7.6 horizontal over the M7-blocked cores).
- The strip screen counts a feed-through once per strip if a station sits in it; it does not separate bits running along the strip
  from bits crossing it.
- t47: the 5 ps ECO pass was not run. t75: the state of the stopped job is lost.
- t37 form c is on the B3t block; its landing contract changes in B6gsl and again in B6gslcf.
- col_h10_r1: no build on B6gslcf exists; the setup sources are inferred from the repair table, not from a path report.
- phy__t1: I did not rerun the census with pin positions; 160,000 is a bound from HPWL. Whether the PHY macro itself delivers
  clock to the wrapper flops (which would change the tap count) was not checked.
- B6gslcf was still in bind when I read it (log ended at G0_RC=1); I did not check whether it was adopted.
- Scripts used are on epyc7 `/tmp/fpd_{tdump,pdiff,slot,strip}.py` and epyc8/9/10 `/tmp/fpd_cong.py` (read-only).
