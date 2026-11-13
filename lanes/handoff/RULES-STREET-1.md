# RULES-STREET-1 handoff (R-STREET owner)

Updated 2026-11-13 07:56. STATE: DONE, lane stopped.

- Rule: lanes/RULEBOOK-1113.md section R-STREET (final). Tool on main 5eefdbe2fa (branch claude/rules-street-1113 @ 8dd3028a50): tools/die_plan/street_rule.py check / legalize, check.py --street-rule (off by default; pass warn on every G0, error from a die's R-STREET plan event).
- Counts (wave plans 11-13): S81 170 of 349, QC 30 of 73, KV 21 of 50, HEAD 0 new-kind (5 types under rule 1 / columns). Tables lanes/rules-street-1113/.
- Proofs recorded (one-shot GRT overflow): t28 6.67M -> 3.72M (form A) / 4.25M (form B); c1x t3 5.51M -> 1.28M. No type GRT-clean on streets alone.
- Rulings given: HEAD-97 abutted-tile sparse outline faces (legal at 12.96); S81-FORMS-1 use form A; rule 5 is a WARN.
- Open, for a successor if wanted: (1) tool does not yet carry the sparse tier for core-to-outline faces (prints outline_street need 43.2; waived by the ruling); (2) relay columns and taps are not counted as stations by the tool; (3) c1x 50-iteration probe left running on epyc7 rules-street-1/proof2/dsdv_slice_c1x_C__t3/geom (ends by its 5400 s wall); (4) KV legalize dry run never finished; (5) private dirs /srv/opentallas-scratch2/claude/rules-street-1 on epyc7/8/9 and intel2 (about 25 GB on epyc7: two bind outs, three kits) can be deleted after COORD has read the proof; the worktree epyc7 rules-street-1/wt is merged and can go.
