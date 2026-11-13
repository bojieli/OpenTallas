# FRAME-FORMS-1 handoff (S81 frame family col_h9/col_h10; Fable lane; COORD) -- started 2026-11-13 06:15 PST

## Scope
- DIEVIEW-S81-1113 F1: 216 frame tiles / 26 kit items / 0 signed off. ONE template re-pack under R-STREET-1/2/4 (cores move/rotate,
  never reshaped), applied to all 26 items as template + per-item deltas; plan delta; G0/G0C; strict bind; lane latency; 2 private
  place/GRT/route proofs; ONE S81 frame event READY (adopted after 11-15 04:00). Coordinate with S81-FORMS-1 and HARD-S81-DSDV-1.

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/frame-forms-1 (own clone of hub:OpenTallas), branch claude/frame-forms-1-1113.
- Work dir epyc7 /srv/opentallas-scratch2/claude/frame-forms-1/ (insp1.py, rframe.py type renders, base_png/).
- Base plan: wave plan src_s81_main_7073a6b4a5/physical/die_plan/s81/plan_h2_2249.json sha 18c864518844 (ready12b-A).

## State
- 06:2x: read DIEVIEW F1, RULEBOOK R-STREET/R-REACH, METHODOLOGY 12. Rendered the 26 base types (base_png/). Clone running.

## Resumed after FRAME-FORMS-2 HANDBACK (07:26). Work moved to epyc4 (epyc7 was at load 168).
- epyc4 worktree /srv/opentallas-scratch3/claude/wt/frame-forms-1, branch claude/frame-forms-1-1113 (on origin, b74d4c6515,
  off main 5eefdbe2fa). Work dir epyc4 /srv/opentallas-scratch3/claude/frame-forms-1/ (w/plan_A.json = ready12b-A 18c864518844).
- Tools in the branch: events/s81_frame_spine_1113/ (frame_spine_seed.py = the template, park_taps.py, cp_frame.py, finalize.py,
  run_types.sh, README.md).
- TEMPLATE "FRAME-SPINE" (differs from FF-2's FT1 sketch; FT1 was not coded): the east strip becomes a centre spine. W pair at
  x 17.28, E pair at x 859.68; each pair's 7 cfg ROMs stand beside it in 3 abutted columns (3+3+1, 19 um slot under every ROM
  S pin face); centre street 59 um holds the type clock tap. Row street: station + payload at the spine mouth, bs centred
  between the two S pin groups 51.84 under the elements, seq in the street 43.2 under the element, bn 46 above the N pins.
  bf group keeps its x (W half-group -21.6 so the front-roots faces get 43.2), its ROMs/seq/station in one band 43.2 below it.
  Nodes: E zone beside the bf group + row-street outer ends, by connectivity and station reach.
- RESULT so far (2 reps: col_h9_r2 clce45cab5 pv06a1adf6, col_h9_r1 cl49d7a23e pv047ea3b3): core_place applied, EQ ok, every
  station keeps its register count, R-STREET hard kinds 37 -> 0 and 51 -> 0 (street / wall / outline_street / face_street /
  station_alley); left: 18 sliver + 4 outline_sliver WARN per type (ROM S-pin slots, base bf half gap, W margin 17.28).
  route_supply p99 5.9 -> 3.6 and 5.3 -> 3.5. Renders: epyc4 work dir cp1/png.
- OPEN: (1) 13 r0 items (cf 281x69, E/W windows, ft lanes) are seeded but cf has no site and node sites are short; (2) 2
  col_h10_r1 items (two bf groups) do not fit vertically (need 1430 of 1227) and need a variant; (3) all-type run, chain
  (G0/G0C, strict bind, latency), 2 proofs: not started.

## 07:5x-08:xx state
- Template fixes after the first runs (all in branch b74d4c6515): ROM signal pins are on the S face, so ROM columns abut at
  3.0 um sideways (pitch 41.04, 0.108 grid) and keep a 19 um slot under each ROM; the tool wants abut (< 4.32) or >= 43.2
  wherever >= 16 pins face a gap, so bn stands 46 um above the element, seq 43.2 below it, station | payload 43.2 apart.
  core_place quirks handled in cp_frame.py / finalize.py: base outline overlaps 0.54 / 0.89 um; the type clock tap rode with a
  core (restored to base 725.76, 613.44; it is free in the centre street); core taps set to base + core displacement.
- RUNNING: Opus sub-agent FRAME-FORMS-1-VOL on epyc4 (scope: 132 pv types of col_h9_r2 x5, col_h10_r2 x4, col_h9_r1 x2):
  all-type run + merge + finalize, added_tap_recentre, chain, G0/G0C, strict bind, lane latency, 2 private proofs
  (col_h9_r2 clce45cab5, col_h9_r1 cl49d7a23e). It appends lines under "## VOL sub-agent" below.
- r0 (13 items, 72 tiles) NOT in this event. Measured with the template as is (epyc4 work dir r0dev/, why0.py prints the
  blocking rule): col_h9_r0: only two blockers. (a) cf (280.8 x 69.12, 1,170 N + 1,179 S pins) has no site: at its base
  spot it collides with the E pair. (b) on p1-p3 the bf group may not move: ft0 bit sites stand at (1142.6, 980.6+) and
  (473-475, 1150+) beside the base bf cores. Variant that keeps bf at its base y 950.4: row street channel 34.56 -> 21.6
  (S street 129.6), M0 47.52. cf site in the E zone beside bf (x 1144.37, abutted to the E half-group), 43.2 streets N and S,
  clear of the E-face window span: p1-p3 (window y 740-980) cf y 984.96, node rows y 864 and 1097.3 (6 nodes) + 6 row-street
  end sites = 12; p4-p6 (window y 981-1221) cf y 885.6, only 3 node sites above it + 6 = 9 of 12: three nodes still need a
  home. W pair stands 17.28 off the W face inside the W window span (xo_o0 1104 bits): face_street; moving the W unit +25.92
  leaves a 33 um centre street, so the W window rows need their own answer. col_h10_r0 (bf in the middle, 6 ROM groups, 4
  stations): the template applies mechanically but leaves 23 street + 2 face_street + 4 outline_street (bn / t3 at the N face
  under the N window, second bfp group c5/s5 and t3 unassigned).
- col_h10_r1 (2 items, 12 tiles): two bf groups + two rows need 1430 um of 1227: no fit; needs a variant without the bf ROM
  band (ROMs beside the bf groups) or a different unit order.

## VOL sub-agent
- 08:04 T1 all-type run (epyc4 frame-forms-1/all1): 5/11 items ACCEPTED (cl49d7a23e 54, clf32cde8d 6, cl774acf45 5, clb8d86cd5 6, clce45cab5 43 = 114 types, hard street 5112->0); 6 REFUSED at base: 4 col_h10_r2 (applied False, link-length tviol 1/143/20) + col_h9_r2 cl87f3ff59 (tviol 185, SEED-MOVED) + clc9ad8f7e (SEED-MOVED u_e13w.u_view.u_c -> 1 street/type). Chain running.
- 08:12 T2 taps: core_place had CARRIED 152 added taps with their cores (e.g. clk_t20 1070 um west); restored to park_taps xy (all kit-legal, 0 legality moves; added_tap_legalize.py). added_tap_recentre: col_h9_r2 items 0 failing; col_h9_r1 BOTH items (60 types) fail clk_t21 radius 288.7/200 (x1.10 slack) from reset relay rst_rl_77 (1429.32,669.32), no legal single-tap move -> needs an added tap = design call: col_h9_r1 STOPPED (left at base). Chain re-run r2-only (3 items, 54 types).
