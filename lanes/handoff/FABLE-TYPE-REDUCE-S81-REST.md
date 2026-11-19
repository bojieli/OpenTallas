# FABLE-TYPE-REDUCE-S81-REST handoff (started 11-19 01:16 PST)

Scope: S81 families leaf, slice_station, serdes, dsdv_slice_c1x_C, svc_lo/hi_dsdv_svc_rs, kv_leaf (col families: FABLE-TYPE-REDUCE-S81-COL).
Lane dir: epyc9 /srv/opentallas-scratch2/claude/fable-type-reduce-s81-rest (a2..a12.py analysis scripts, census_*_v2.json, dedup_d8f.json, repo/ lane clone).

## State 11-19 01:5x PST: Step 0 done, no family passes, nothing running
- Posts: STEP0 01:2x (serdes PASS and leaf "faster" lines are WITHDRAWN) and RESULT 01:5x (final).
- Pushed: main f5f0d744f8, tools/precheck/type_census.py + 4 tests (bound RTL by plan module name; traffic_classes, landing_classes,
  estimate_no_reroute). No plan flag `type_template`, no generator change, no kit, no waiter.

## Why (measured on D8f plan_h2_2249.json, D8e bind RTL, registry 01:17)
- S81 types split on three position axes: (a) die traffic through the type as ft_slots (no streets; 73 of 75 leaves carry foreign lanes),
  (b) clock landing cohort (landing_contract + count-aligned strap set), (c) wrapper extras (rst_o export, sid parameter default, tap names).
- A pin template removes only window positions. Classes with windows re-slotted, no lane moved: leaf 65, slice_station 39, serdes 4,
  c1x_C 9, svc 13, kv_leaf 5. With the landing cohort: leaf 74, serdes 11, slice_station 46. S81 395 -> 274 (lower bound 51).
- schema.py ("bus is unbound ... tie-offs are not allowed") blocks a superset FT template until bind / landing / K-strap code supports it.
- Signed now: slice_station 35 of 46 (7 route, 4 pre-route); every other family here 0.
- serdes chain facts (for a later event): 4 shore chains; E-form types t2 t14 (0 FT), t1 x2 t16 (2 FT), t3 t15 x2 (4 FT), own bus on slot
  0 / 1 / 2 of the inner face, FT straight with 8 stations; S-form ends t4 t12 t13. A shift form (own bus on slot 1, W slot 1 -> E slot 0,
  W slot 0 -> E slot 2) keeps t12 / t13 and the slice_station pins, permutes the W slots of t4, and needs 9 stations on the 450 um jog.
- leaf floorplan check (a10.py): cores are 34 % of the leaf area; t69's core placement clears the FT station sites of 11 of 75 types, t27's 7.

## Open decision (COORD / owner), not started
S81 slice re-floor with street columns: leaf 75 + c1x_C 9 + kv_leaf 5 -> about 8 types + about 16 FT-only street types; street about 240 um
(0.6 track use), die x about +6 %, 35 signed slice_station types get new pins, one landing contract per template; 3 to 5 days before the
first template kit. Recommendation: decide at the first D8g leaf GRT TT read; start only if the FT-heavy leaves (t8 t72 t3 t75 t67) fail on
congestion classes after the common-logic fixes.

## Next for a successor
- Nothing is pending. If the re-floor is approved: rows = street column per slice half in gen_plan_v2.py, ft_channel_route with "no foreign
  FT in leaf", uniform landing contract for the leaf template, then one template kit to GRT TT (r712) before the bind.
