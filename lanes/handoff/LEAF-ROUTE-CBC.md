# LEAF-ROUTE-CBC handoff (Opus, 11-22 23:3x PST)
Scratch: intel2 /srv/opentallas-scratch2/claude/leaf-route-cbc (renders/, probe/, moves_*_j7.txt); all gen hosts /srv/opentallas-scratch3/claude/leaf-route-cbc (kit/ lrc_dump.tcl lrc_qgrt.tcl lrc_qrun.sh; db/; dump/; qgrt/); clone epyc9 .../leaf-route-cbc/clone.
DONE
- 10 worst renders + verdicts (GEOM-REVIEW.md); all 80 VIS-COVERAGE rows have verdicts: LANE-JUNCTION 73, FT-CORRIDOR 6 (kv t1/t2/t5 NONE-NEEDED), CORE-CHANNEL 1.
- ADV-ROUTE-DEMAND on main f01b2d6317 (tools/die_plan/adv_route_demand.py + test). Calibration in the module doc: location recall median 99%, precision 4-32%, no within-family ranking (Spearman <= 0.34).
IN FLIGHT
- J9-LEAF-LANECH family form: kit-only OT_MACRO_MOVES spread junction set (lanes, vp.u_b0/b1, vn_a/vn_b) to channels >= 40 um, no growth (lanech.py spread_fit in my scratchpad; copy pending to scratch). Moves gate PASS t44, t39.
  Probes (goal place, J7 wave tree): intel2 probe/p44.sh -> spec_t44, spec_t39 (logs run_t44.log run_t39.log).
  Baseline quick GRT on J7 3_place.odb: epyc9 ot-run lrc_qrun.sh base_t44 / base_t39 -> qgrt/base_*.
  NEXT: qgrt on probe 3_place.odb, render, READ; if hotspot gone -> PROBE-PASS leaf rows, 2 sealed --goal route + 1 OT_PROBE_THROUGH=1, then in-plan row (leaf_regrid.py nudge/retap style, re-site stations under moved cores: moved cores cover 219/918 t44 sites -> needs re-site) to S81-J6-ASSEMBLY-R5.
- R10 keeps t50/t68 kit-only moves; LANECH supersedes on overlap once gated, tell R10 first.
