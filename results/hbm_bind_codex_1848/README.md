# HBM bind continuation, 2026-10-29 18:48 PDT

The inherited DIE-HBM-24 d23c plan already implements the COORD-approved HBM-044(A) removal of eight SU side cores that have no cells in the selected source. It also removes eight clock taps and instance-level clock/core connection sidecars. There are no side buses, contents or internal stations to remove (the inherited delta fails closed if those exist). The source is unchanged and no data cycles change.

Plan: intel1 `/srv/opentallas-scratch2/claude/die-hbm-24/plan/d23c/die_plan.json`, SHA256 `77d613ccd6003946e6d497198890d3550251cd6a9ea1354356f052b4459651ae`. Inherited G0 PASS; G0C retains eight errors. `inherited_side_drop.py` is preserved from the interrupted worktree; `side_drop_report.json` is its existing receipt.

The inherited b3 launcher failed before binding because it did not seed `out/asbuilt.json`. The corrected job reuses the immutable HBM-BIND-13 g3 elaboration cache (120,938,705 bytes). Own b1 then exposed a sparse checkout missing the committed dead-input proof; b2 exposed missing selected RTL definitions. The exact proof and physical/RTL trees were restored. These setup failures are retained at intel1 `codex-hbm-bind-1848/d23c_b{1,2}`.

Shared diagnostic collector commit `47eed2ef4` adopts interrupted DIE-HBM-24 `--all-gaps`. Default fail-fast behavior remains; opt-in emission accumulates existing core-reset, parent-ID and glue errors and withholds the bound top when gaps exist. Two missing reset leaves are now both reported. The regression fails on the baseline; the patched emitter, wavefront and identity tests pass 16/16. ROOT-MERGE integrated it in main `5d0d71f1e9a`.

Actual strict diagnostic run: intel1 `/srv/opentallas-scratch2/claude/codex-hbm-bind-1848/d23c_all`, ot-run unit `oth-ubuntu-3219295-1793325231`, Python PID 3219493, `run_bind_all.sh`; read `bind.rc`, `bind.log` and `out/bind_report.json`. The report is pending at this checkpoint. No P&R or STA was submitted by this lane.

## Explicit reset park, 19:03 PDT

The first all-gap run terminated with a collector KeyError after it recorded an invalid parent ID and later tried to emit that leaf. Follow-up `e37f82f82` skips only already rejected ID leaves. A new actual emitter regression fails the previous collector and passes the fix (four tests PASS); ROOT-MERGE owns integration.

The corrected actual `d23c_all2` run finished strict FAIL: **163 errors = 92 UNPLANNED (82,285 bits) + 71 EMIT**. Unmapped, tied, undriven and multiply bound are all zero. No incomplete bound top exists. HBM-044 side-core errors are gone. EMIT contains 60 parent-ID messages (including aggregate declaration summaries) and 11 missing core-reset leaves: eight SU pretrees (q0/q1/q2/q3 plus physical twins), root SW collective root and two root HC steady tails. Full immutable `bind_report.json` is retained here.

Source-ID preparation completed immediately before the explicit reset was received: `source_ids.py` derives each selected cut ID from original Yosys literal terminal connections, never guesses the quarter/group formula. It produced intel1 `codex-hbm-bind-1848/d23c_ids/die_plan.json`, SHA `128ad3093cb45b1e7dc9d0cbfbf44aa0ad01f67cddd1b6881a44693bcdf97823`, changing 52 descriptors/cores, zero RTL and zero cycles. `source_ids_report.json` lists every original source terminal and before/after value. This candidate has **NOT RUN G0/G0C or bind** and is unadopted. No new jobs or engineering after receipt of reset.

Next: gate the ID candidate, rebind with all gaps, then materialize exact source-owned cuts for the SU pretrees/root SW/root HC steady tails. Die plan owner handles the 92 UNPLANNED crossings. All own jobs are terminal; no inherited jobs were stopped. No new OWNER question.
