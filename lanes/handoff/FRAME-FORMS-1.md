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
