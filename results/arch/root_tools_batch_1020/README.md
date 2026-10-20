ROOT tool batch 2026-10-20

Base for paired full ROOT suite: 4260f7b808c7a6e02718da139eb4e0c43bf7c625. Candidate snapshot: fc3f86a42 plus no later tool changes at pack time (exact candidate patch SHA256 below). All runs on ot-epyc5 through unpinned ot-run; no local simulator/OpenROAD builds.

Changed behavior:
- ck_insertion skips only arc-less BLOCK clock pins after unique clock ownership is established; records OT_MC_RAW_NOARC. Live arcs, non-BLOCK pins, failed arc queries, missing/ambiguous clock owners retain existing handling. Landed RAW_PIN validation remains the independent boundary obligation.
- Every measured root is judged against the existing TT/FF 80 ps pin-flop rule. Roots without pin-flop arrivals are recorded as INFO. Existing multi-root-specific admission is preserved.
- Source-binding retention checks use compensated nested child-flop boundaries as well as scalar child-flop/boundary evidence (7524fabdc, follow-up after full snapshot).
- KV generator adds hck boundary Tcl restoring hclk IO after io_ref without adding clocks or exceptions. The six existing kit outputs and hroot RTL/view integration belong to KV lead, excluded here.
- lp audit refuses direct input/alias reads across multiple regions; generator output unchanged.
- CDC constraints install all exact bounds before finite-path checks (cb43f20fe cherry-pick of c9601c494). No bound, finite-path obligation, or pre-MM deferral changed. Tested separately after full snapshot.
- Registry classifies 6ebf7706a as neutral: its sole guarded path is a NEW kit-local spec generator, with no shared gate-validator edits. Urgent commit568463f6c can be cherry-picked alone.

Full ROOT suite: closure_loop base19 failed/1128 passed vs candidate19 failed/1137 passed; ref_tile93 failed/606 passed on both; fleet7 failed/52 passed on both; landed_parent base8 passed/candidate12 passed. NO new failure IDs in any cohort. Existing failures include unavailable physical fixtures/tool dependencies and existing assertions; these are baseline comparison results, not an all-green claim. Full raw failure output is committed. Historical Git objects were supplied for the two lp tests requiring 799eebe53 sources, making all lp tests pass. The known unbounded fleet wait test was deselected symmetrically per ROOT4 precedent.

Suite2 earlier had one additional helper-overlay restart failure; isolated replay full helper-overlay file passed40 tests+6 subtests on both sides, and suite3 full rerun has identical fail sets. Original failed targeted run used a misspelled CDC test path and old sparse tree; retained as targeted_cdc.log. Corrected targeted2 run: every-root7 passed; clock-source+guard26 passed; CDC batching/seams/registry14 passed+13 subtests. Boundary2 passed. LP selftest PASS with unland mutant rejected; regional bindings/reset mapping and negative mutants PASS. Urgent registry4 passed.

Fleet IDs: full suite3b client2621532 unitoth-ubuntu-1366950-1792481939; targeted2 unitoth-ubuntu-1447123-1792482050; both terminal. No owned jobs remain. Remote artifacts /srv/opentallas-scratch/claude/codex-root-tools-suite-1019; local scratch /home/ubuntu/scratch/codex-root-tools-suite-1019. suite3.sh and targeted2.sh preserve exact commands. Native pre-gate census policy applies to physical tiles; no new physical tile/gate launched by this helper batch.

Daemon sync after merge: tools/closure_loop/ck_insertion.py, tools/closure_loop/helper_overlay.py (if urgent registry not already synced), tools/ref_tile/pre_route_gate.py, tools/ref_tile/source_binding.py, tools/ref_tile/cdc_sync_constraints.py. Repo consumers additionally use tools/landed_parent/lp.py and tools/qwen_kv_die/kvs_tile_kits_rep.py. Root owns daemon sync/drain policy; this lane changed no live daemon files.

Candidate patch sha256: 218030cf7756f958e0ed907ac069438dcb1c7f4e24fb16e141042218cd429196
