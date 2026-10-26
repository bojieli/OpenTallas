# Full helper comparison on complete frozen source

The complete 42 GB tracked main 60898520a archive was materialized from the fleet git mirror. Baseline ran all four directories through `python3 -m unittest discover -s tools/<suite>`. Only the two admission helper files and new regression test from 44cbf2e32 were replaced, then the same four commands reran. The complete raw logs and exact failure-name comparison are here.

Fleet: EP7 unit oth-ubuntu-464373-1792731437, normal unpinned ot-run MEM16, threads4, disk100. Main baseline: closure_loop 1092 / ref_tile306 / hier_contract116 / tt_views36 =1550 tests. Candidate: same counts except ref_tile308 =1552 tests. All existing failure/error identities match; ZERO new failures/errors. Two added tests pass. Both runs retain 2 failures and17 errors, plus17 skips total, from existing environment/import/fixture issues; this is a zero-regression comparison, not an all-green claim. Detailed names and per-suite summaries are in full_comparison.json.

Earlier initial broad harness used pytest, which is unavailable on this host; that attempt did not execute tests and was not used for qualification. No source or route in another lane was changed. ROOT remains responsible for required merge checks and daemon sync before kshare submission.
