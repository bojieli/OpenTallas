# INFRA-FIRST-QC-R28 (2026-10-27): PG option A (VSS cut under the clock-mesh straps) + D-QC-A0-R3B, one QC plan event

Base: claude/qc-infra-r27-1027@3e4a794033 (codex/qc-clock-1027@77c339e5bc + R27 census) + cherry-pick of
claude/qc-a0-plan-delta-1027@ba3b9825ea (D-QC-A0-R3B, COORD approved 11:2x to ride this plan event).

## 1. PG cut (COORD 11:08 OPTION A) -- DONE, gate PASS (own runs, CHECKED as runs; NUMBER-CHECK pending)
* Tool: `die.pg.grid[].net_holes_um {net: [rect]}` (schema) = exact per-net cut-outs, honoured by `die_infra.pg_rects`
  (clock router / shield ties / mesh inventory / IR model) and `die_trial.pg_stripes` (GRT OBS); pdngen builds get the
  same cut from `post_pdn_cut.tcl` (ORFS `POST_PDN_TCL`, runs after pdngen: cuts the VSS M8/M9 sboxes and drops the
  VIA89s inside the holes). Generator + checks: `tools/die_plan/pg_mesh_cut.py PLAN MESH OUT`.
* Rule: one hole per merged collinear strap run on the strap's own layer; across = clock half-width + NDR space
  (0.24 um at 8w: only the VSS stripe the strap sits on); along = shield end extension + space (0.64 um past each
  strap end, so the kept VSS neither touches the clock metal nor merges with a shield end). Kept pieces that meet no
  perpendicular VSS stripe are cut too (178 M8 tails, 8 um, east of the straps whose end column is cut).
* QC plan (physical/die_plan/qwen_compute/die_plan.json), mesh = prototype8 export8 mesh (`mesh_straps.json`,
  clock_spec sha256 956139e1...): holes M8 356 / M9 433; VSS removed M8 5,266.0 mm (5.55 %), M9 5,269.9 mm (5.55 %);
  VDD untouched (0.0 um).
* Checks (`pg_mesh_cut.json`): mesh clock metal vs PG 3,299 shorts -> **0**; drawn-shield wide merges 6,598 -> **0**;
  VSS M8/M9 graph **1 component**, 0 floating pieces, 0 cut ends without a VIA89 within one pitch (8.64 um); die-edge
  stubs max 17.28 um (uncut stripe ends whose last column is a cut M9 strap column; info).
* Render `pg_cut_mesh.png` (viewed): corner window (strap corner 1632.96/250.56) and a mid-die strap crossing; the VSS
  stripe is absent under each green strap, VSS shields (black) flank it, VDD (red) unchanged.
* G0 / G0C on the combined plan (R3B + cut): **0 E / 111 W**, identical to the R3B delta and the base
  (`g0_combined.txt`, `g0c_combined.txt`, `diff` vs results/qc_a0_kits_1027/plan_delta/g0*_delta.txt empty).

## 2. IR on the cut grid (task 4) -- own PDNSim runs, UNCHECKED (NUMBER-CHECK please), `ir_window.json`
Deck = copy of the QC-PG-WC core_centre window (864 x 864 um at die 15171.84/12700.8, 0.5666 W = 0.759 W/mm2
worst-case uncapped AR, 64 window-local bumps, open window edges). Changed only: PG stripes (pg_regions.core_stripes_tcl
form incl. -starts_with POWER), the R28 cut (4 M8 + 1 M9 straps in the window; cut 5 stripes, 891 / 2,791 VIA89 removed),
VSS solve added. check_power_grid VDD + VSS OK in every run.

| grid | VSS worst / avg mV | VDD worst mV |
|---|---|---|
| plan die.pg.grid 0.48@8.64 M8/M9, uncut | 111.0 / 68.6 | 111.0 |
| plan die.pg.grid, R28 cut | 113.0 / 71.8 | 111.0 |
| QC-PG-WC IR grid M8 0.48@2.16 / M9 0.48@1.728, uncut | 33.2 / 21.3 | 33.8 |
| same, R28 cut | 33.3 / 21.5 | 33.8 |

* The cut itself costs +0.1 mV (dense grid) / +2.0 mV (plan grid) VSS worst: small, as expected for 5.5 %.
* **FINDING (needs a ruling): the plan die.pg.grid (8.64 pitch) is NOT the IR-closed grid.** At this power it is
  111 mV, 3.1x the 35.45 strict bound, cut or not; even scaled linearly to 0.417 W/mm2 it is ~61 mV (UNCHECKED
  arithmetic). The 33.5 mV QC core IR (and NUMBER-CHECK 18.4 mV at 0.417) was solved on the denser grid, which the
  clock planner and the dry build do NOT use (dry build pg_source = plan die.pg.grid). On the dense grid the mesh
  straps still sit on VSS (0 mod 2.16 / 1.728), so the same cut applies, but its 0.6-um / 0.384-um stripe gaps leave
  no drawn-shield clock track at all, so the whole tree/mesh track model changes. The QC PG grid must be decided
  (plan grid + more metal elsewhere, e.g. M9 width as on HEAD, or the dense grid + flank-mode clock) before die STA
  numbers can count (12.4e: PG IR closed before signal GRT).

## 3. Dry build on the cut grid (task 3): NOT 0. Root cause = track geometry, not the VSS shorts
Run intel2:/srv/opentallas-scratch2/claude/qc-infra-r28/c_dry10 (prototype8 plan + R28 cut, same export8 clock_spec,
OT_V2_COLLECT_PLAN_ERRORS=1): **15,916 errors** (R27 uncut 15,774; own runs). The cut removes the 3,299 mesh/VSS shorts.
It frees no tree track, because the strap itself sits on the cut lane. Errors by edge NDR (`dry10_plan_errors.json.gz`):
driver jog 4w 6,547 / 16w 1,186 / 2x16w 223 / 8w 23; trunk 16w 4,343 / 2x16w 1,631 / 8w 438 / 4w 312; reserve_overflow
109; net_trunk_layer 12. Failing edges: 16w 5,361/7,513, 2x16w 2,118/4,770, 8w 461/1,238, 4w 7,303/19,895.
Probe (`probe_block.py`, monkeypatched TrackRouter.place, no source change; `probe_block.json.gz`): 15,500 M8 failures
lie inside the island pin keep window (4.91-5.72 um = pin +-2.455 riser). 13,432 have another tree net in the window,
and 2,069 have only PG plus the drawn shields of other trees. 295 are M9 trunk failures (free 17.28-um window, tree-blocked).
Geometry (CHECKED arithmetic from the NDR table + 0.48@8.64 VDD/VSS, VSS on the island pin lane). Legal centre band per
4.32-um PG gap: 4w ~[0.64,3.60] (~4 tracks); 8w [0.80,3.44] (~2-3); 16w drawn [1.70,2.12] (**1 track**, because the
shield may not merge with VSS: 1.12 > 0.99975); 2x16w drawn **none** (VSS-edge to VDD-edge needs 1.0+1.28+1.0+1.28+1.0 = 5.56 um > 3.84), flank [1.88,2.44] (1).
The island window covers exactly 2 gaps. So an island row holds at most 2 wide (16w/2x16w) conductors that overlap in x,
and the shields of each wide conductor fill its gap for the 4w jogs too. Demand is higher than that, hence the errors.
=> Planner fix needed (task 2, NOT done here): allot tracks in the planner (qc_clk_mesh3 export) per island row and per
PG gap, using this capacity table. Wide trunks leave the island window via an M9 drop to a free gap (L-form, like the
R12 l_drops), or drop to 8w where the stage RC allows; driver jogs stay on 4w. This is a planner/stage re-solve owned
by the QC clock planner. It depends on the PG grid ruling (section 2): on the dense IR grid no drawn 16w track exists at all.

## 4. Not run (blocked)
GRT0 >=50 it and related-pair die STA (die_sta_related.py, TT 250 / FF 202.5) did not run. The clock component still
does not dry-build (15,916 plan errors), so there is no clock to route or time. Same blocker as R27.
R25 DRC unit oth-ubuntu-1828381-1793110415 (intel2 qc-mesh-r25/drc, old R24b geometry, no PG): 19,213/20,857 boxes at
11:56, still LIVE. Collect drccls.json + samenet_gaps_drc.json when chain.sh prints R25_DRC_DONE.

Note: the PG cut was applied to main's physical/die_plan/qwen_compute/die_plan.json (H 26265.6). The dry build and its
mesh come from the prototype8 plan (H 26317.44, Codex candidate lineage). The straps lie inside both outlines, and
the cut depends only on the strap coordinates.

## 2. COORD 12:1x ruling: ONE wide coarse-pitch grid (supersedes the section-1 cut; no cut needed)
* `die.pg.grid[].pair_spacing_um` (schema): VDD/VSS PAIR per pitch, second stripe at edge spacing `pair_spacing_um`
  (pdngen `-spacing`), honoured by `die_infra.pg_rects`, `die_trial.pg_stripes` and `pg_regions.row_spec/stripe_tcl`
  (test `test_pair_spacing_wide_pair_and_pdngen_spacing`; 20 tests PASS).
* QC die.pg.grid (adopted, net_holes removed, rest of die_plan.json byte-equal as JSON):
  M8 1.92 um @ 8.64, offset 2.86, pair spacing 1.0 -> clock gap 3.80 um centred on every 0 mod 8.64 strap lane;
  M9 2.26 um @ 8.64, offset 2.69, pair spacing 1.0 -> clock gap 3.12 um.  Metal fraction M8 44.4 %, M9 52.3 %
  (dense 0.48@2.16 = 44.4 % / 0.48@1.728 = 55.6 %; M9 2.40 = 55.6 % leaves 2.84 um and the drawn 8w shield 0.86 um
  from VDD < 1.0 wide-table spacing -> needs flank mode; 2.26 keeps drawn shields).
* `qc_pg_wide_check.py` (mesh clock metal + drawn VSS shields vs PG with the ASAP7 wide-metal spacing table, mesh =
  `mesh_straps.json`): 0 violations; min gaps M8 mesh 1.74 / shield 1.34, M9 mesh 1.40 / shield 1.00 um (`pg_wide_check.json`).
* IR window (same core_centre 0.759 W/mm2 deck, `ir_window.json`, UNCHECKED, gate 35.45 mV):
  wide226 (adopted) VSS 30.9 / VDD 27.3 mV worst (avg 16.0 / 15.3); wide (M9 2.40) VSS 29.8 / VDD 26.6 mV.
* G0 / G0C on the combined plan (R3B + wide grid): 0 E / 111 W = base (`g0_wide.txt`, `g0c_wide.txt`).
* Open: 2x16w drawn needs 5.56 um between stripe edges, more than the 3.80 / 3.12 gaps at the dense fraction ->
  the planner per-gap allotment keeps 16w/2x16w trunks out of the gaps (M9 drop out of the island window, 4w jogs);
  TrackRouter must use the wide-table 1.0 um spacing to wide stripes (it uses NDR space today).
* R25 DRC (unit 1828381, `../r25_drc/`): 24 unique markers, all M8 Min Step at cell/net ends; same-net VSS shield gaps
  408 (24 at 0.04, 384 at 0.28 um), 0 marked -> PASS.
* Render `pg_wide_mesh.png` (viewed, `render_wide.py`): strap corner 1632.96/250.56, M8 + M9: each green strap with its black VSS shields sits inside the clock gap between pairs, clear of red VDD / blue VSS.
