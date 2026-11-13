# RULES-STREET-1 handoff (R-STREET owner)

Updated 2026-11-13 05:47.

- DONE: rule + tool. origin claude/rules-street-1113 @ 59858adeb6 (off main fbfb4fc6a6): tools/die_plan/street_rule.py adds face_street, station_alley, transit_street to check / G0 --street-rule / legalize; 33 tests pass (`python3 -m pytest tools/die_plan/test_street_rule.py`). Worktree epyc7 /srv/opentallas-scratch2/claude/rules-street-1/wt.
- DONE: counts on the wave plans (final code): S81 170 of 349 (face 129, station 128, transit 84), HEAD 0 of 7, QC 31 of 73, KV 21 of 50. Tables in coord lanes/rules-street-1113/*_violators.tsv. JSON: epyc7 rules-street-1/out/s81_g.json, epyc8 rules-street-1/counts/{head,qc,kv}_g.json.
- DONE (interim): lanes/RULEBOOK-1113.md section R-STREET, coord/state beeb8b2b83f. Draft + value files on localhost scratchpad rs1/ (rstreet_section.md, vals/*.txt, fill.py); insert with intel2 /srv/opentallas-scratch2/claude/rules-street-1/insert.py.
- RUNNING on epyc7 /srv/opentallas-scratch2/claude/rules-street-1 (R), all private, via ot-run:
  - R/proof2/ot_s81sl_leaf__t28: t28 with face + station rules only (plan_rs1_d.json, bind_out). Placed; GRT probe running (geom/grt.log, 5400 s wall). Early AUTO-GEOM: channel_h 4.77 vs baseline 4.13 = no gain, which led to the transit rule.
  - R/proof3/ot_s81sl_leaf__t28: t28 with the full rule incl. transit (plan_rs2_a.json, bind_out2, chain2.sh). In kit generation, then place, then geom. This is the proof that counts for t28.
  - R/proof2/dsdv_slice_c1x_C__t3: c1x t3 (its plan is the same under the full rule). In floorplan/place (baseline place took ~2 h), then geom.
  - R/base_geom/{ot_s81sl_leaf__t28,dsdv_slice_c1x_C__t3}: baseline 3_place.odb GRT probes on the same host with the kit settings (base_kit/). epyc9 baseline t28: 5 iterations in 5400 s, not converged.
  - Status in one line: `ssh epyc7 bash R/poll.sh`.
- NEXT: when proof3 t28 and proof2 c1x have auto_geom.json: view run/layout_review/place/density.png and geom/auto_geom.png, compare channel_h / channel_v / GRT iterations and overflow with the baselines, rewrite vals/PROOF.txt + STATUS.txt, re-insert the section, coord-commit, verify on origin, then post READY in lanes/COORD-REVIEW-QUEUE.md (branch, sha, tests, counts, proof) and stop. If a proof still fails GRT, say so plainly in the rulebook.
- Nothing of mine writes into kw45 src trees, wave dirs or ~/coord except this file, the RULEBOOK R-STREET section, lanes/rules-street-1113/ and my queue posts.
