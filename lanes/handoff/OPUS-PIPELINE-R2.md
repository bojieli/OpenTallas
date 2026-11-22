# OPUS-PIPELINE-R2 handoff (Opus, successor of FABLE-PIPELINE-R1) -- own memory across compression

GOAL (COORD, hub 74c7480e40): finish plan->sign-off pipeline proof: parallel bind emit byte-identical to serial + e2e run;
report e2e result + speedup to COORD; if parallel emit proven, land as default on main (ot-push-main with tests).
Predecessor handoff: lanes/handoff/FABLE-PIPELINE-R1.md (push recipe, measurements, defects D1-D3).
Lane clone (adopted): intel2 /srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/clone ; my tmp intel2+epyc8 /srv/opentallas-scratch2/claude/OPUS-PIPELINE-R2/tmp

## Landed by me
- deb04cf0fb bind_emit_par: lazily built record objects (schema.Plan memo clock_landings._physical_clock_plan, per-type _reset_tree_cache) merge attribute-wise.
  Offline plan_merge over run 4's 56 kept worker results (kvob/keep4): PASS (339 paths). Before: UNSAFE on that path.
- a2fe3bc714 ot-build bpc node: BOUND-PARAM findings block only the --type kit's own RTL; else ADVISORY (publish_gate rule). E2E defect D4.

## Runs (all KV D27d3 sealed tree, delta1 plan = FABLE kvob/delta1/plan_c.json)
- run 2 (serial fallback, rt fff2e6eaf2) epyc8 kvob/b_103ca094a86c: bind rc=0 in 4805 s (emit serial), latcheck ok, bpc FAILED (D4). rtl = reference.
- run 4 (rt 387d316c7c, keep4) kvob/b_7df6a93d4f78: parallel fell back (physical_clock_plan), serial running -> second reference (same rt as run 5).
- run 5 (MINE) epyc8 /srv/opentallas-scratch2/claude/OPUS-PIPELINE-R2/kvob5 (rt = private p1_387d316c7ca5 = 387d316c7c + deb04 bind_emit_par), J=8,
  log intel2 OPUS-PIPELINE-R2/tmp/kvpar5.log. Then: diff -r rtl (and top-level json) vs run 4 and run 2.
- e2e1 (FABLE, rt fff2e6eaf2, plan_of_record) epyc2 b_10566ab423ec: serial fallback bind; will FAIL at bpc (D4). Then rerun e2e on main rt (>= a2fe3bc714) --emit-j 8.

## Next
1 run 5 done -> diff; 2 rerun e2e hub on main; 3 if identical: decide default (ot-build already --emit-j auto; bind.py OT_BIND_EMIT_J default 1);
4 report COORD <250 words.
