# FABLE-OPEN-S81-B x9 (stale clock.tap_window / tap_offset per-port class, R-CLOCK-7) - 11-23
Cause: S81 is window form (tap_offset.per_port_ps empty; tap_window.per_port_ps on 395/395 types). A kit clock port missing from the
type row is timed at the flat W_t (gen_phys.port_window_ps); tap_split/added_taps never extended the table.
Census (rt tap_offset_cover census --form all), logs/TSV epyc10 /srv/opentallas-scratch2/claude/fable-open-s81-b/x9/:
- J8 f65f62779bef: 157 types / 1,167 ports missing, 1,274 stale rows (FAIL)
- col compose input 56d5a17e72bc: identical 157 / 1,167
- TAP-GRID dry-run-3 final 2c4a35246162: 163 / 4,739 (leaf 2,846, col_h9_r0 654, c1x_C 393)
- leaf j9F_final3 (epyc9): 156 / 1,154 + t75 UNEVALUATED (13 added taps; reset tap outside interior)
- Wave A candidate 4662b734580b (epyc10 s81-j9-r6/wave_a/tree/physical/die_plan/s81/plan_wavea_4662b734580b.json):
  395/395 OK, missing 0, unevaluated 0, stale 0 -> PASS (core_missing 1 = phy__t1, non-failing). Filled rows never exceed W_t.
  Fill = Codex compose wavea_after_taps_v6.sh step: tap_offset_cover fill --form all after the taps, before replan_die_reset (6,549 ports / 200 types, stale 826, skipped 0).
PRE: rt check_tapoff runs the all-mode census (FAIL TAPOFF-MISSING), so any later delta that appends taps is caught.
Status: x9 GATED on 4662b734580b (PRE-level census PASS); final strict bind/LAT for 4662 running on E10 (Codex/ASSEMBLY gate_parallel.sh).
Re-run on any later compose (epyc10, ~35 min, light):
  python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/die_plan/tap_offset_cover.py census PLAN --form all --tools <tree>/tools/die_plan --out OUT.tsv
Condition: second compose must re-run the fill as its last tap step (any row composed after the fill that appends taps re-opens the class).
