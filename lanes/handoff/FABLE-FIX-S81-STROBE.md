# FABLE-FIX-S81-STROBE handoff (Fable 5.2, started 11-21 11:3x PST)
Lever 5 of lanes/FABLE-CLOSURE-STRATEGY.md: S81 start-strobe place stops (-381..-1252 ps, "hop 116-175 um").

## Root cause (measured)
- report_checks full_clock_expanded on kept 3_place.odb (epyc7, tools >= 3ed87c352a; reports epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-strobe/tmp/read_t16|t18|t29.log, loc_*.log).
- It is DISTANCE. hop_um on the stop line = longest single cell-to-cell hop, not the path. One count origin (u_cland_origin, at the cland_tstart_in pin)
  broadcasts START in ONE clk cycle to every landing reader relay bank and FSTART face flop on the type perimeter:
  serdes t16 origin (2839,474) -> reader_start_ft1_i (55,527) 2.84 mm, 27 wire repeaters, arrival 2022 ps; slice t18 2.28 mm / 19 repeaters;
  slice t29/t6 class: reset relay u_rrl_N -> sync raw reset of u_cland_fstart_ftN_o 1.73 mm / 11 repeaters.
- Same clk both ends, ideal clock, recovery reported apart (+572..+618): not a domain / recovery / fanout artefact. Not multicycle (START is count-aligned, K).
## Fix
- Plan rows clock.landing_reader_start (share_trunk) / landing_writer_start from tools/die_plan/reach_rules.py fix --rules 1 (K - depth at bind, 0 data cycles).
  slice: FAM-S81-SLICE-R4 lever-6 rows epyc10 fam-s81-slice-r3/lever6/j7_lever6_slice_rows.json (hold released 11:5x).
  serdes (t3, t4, t13, t15 cla2127225, t16): epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-strobe/l6s/plan_l6s.json 344dafeef1a7 (= plan_l6 + serdes), pdiff l6s/pdiff_serdes.txt.
  Census all S81 families on J6r1: l6s/check_all_before.tsv (start_reach 105, start_writer_reach 181 types).
- Flow: main b9735df11e, stop line carries path_um / span_um / stages.
## Running / next
- epyc10 gate_l6s.sh (tree kw45/src_s81_pin_3c913dbdfb23_d8j6r1_1117_fxstrobe_l6s + _bind, strict bind + LATCHECK). Log ${tree}_bind.log.
- Next: kit_wave.py private-spec s81 slice_station__t18 --plan/--tree/--bind-out of that tree, run-item, place stop read, route chain to sign-off; same for serdes__t16.
- Not covered: slice_station__t46 (needs reset.local_taps_um, FAM-S81-SLICE-R5).
- Lane clone epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-strobe/clone (pushed, clean).
