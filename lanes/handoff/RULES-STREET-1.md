# RULES-STREET-1 handoff (R-STREET owner)

Updated 2026-11-13 03:56.

- Task: set rule R-STREET once (macro to pin-face streets, macro to macro streets, station alleys), implement in shared die_plan tools, prove on S81 leaf t28 + dsdv c1x t3, count violators per die, write RULEBOOK-1113.md R-STREET, post READY.
- Worktree: epyc7 /srv/opentallas-scratch2/claude/rules-street-1/wt, branch claude/rules-street-1113 off origin main fbfb4fc6a6. Commit 4292e08de5 (street_rule.py face_street + station_alley, tests, check.py help). NOT pushed yet.
- Rule in code: tools/die_plan/street_rule.py (docstring section R-STREET). check / G0 --street-rule / legalize all carry it (cfg face_rule=1 default).
- Proof (private, no wave state touched): legalized plan epyc7/8/9 /srv/opentallas-scratch2/claude/rules-street-1/plan_rs1_d.json (base = wave plan src_s81_main_7073a6b4a5 plan_h2_2249.json; only t28 and c1x t3 changed; legalize --set reach=2000 --set reach_limit_um=2000 so station register counts stay). Moving cores changes the reset collector tree, so the kit RTL needs a re-bind: private strict bind running on epyc9 (rules-street-1/rebind.sh -> bind_out, log bind.log). Next: bind.py kit-rtl per type -> kit_topology prepare-stations -> gen.py phys -> run_kit.sh place -> geom_check.sh (GRT) for both types on epyc9, then view renders.
- Counts: epyc8 /srv/opentallas-scratch2/claude/rules-street-1/counts/{s81,head,qc,kv}.json (street_rule.py check on each wave plan).
- Scratch drawings: localhost scratchpad rs1/ (plan before/after PNG).
- Nothing of mine writes into kw45 src trees, wave dirs or ~/coord except this file, RULEBOOK-1113.md R-STREET section and my queue posts.
