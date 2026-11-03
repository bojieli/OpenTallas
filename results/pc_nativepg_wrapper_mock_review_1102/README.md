# Independent PC entry-wrapper MOCK CONTROL FLOW review

These are Tcl control-flow mocks only: NOT native PG, callback/module, physical correctness, source equivalence or production qualification. No CAD/native module/solver executed. The harness extracts the exact frozen reviewed Python wrapper literal, substitutes only own mock paths and its final exit for an observable success flag, and mocks begin/end/status.

Initial failure receipt CONTROLFLOW_RESULTS_before.json retains the old wrapper SHA and reproduced nonlocal body-return escape: outer source returned code0 without explicit success. Successor reviewed_patch_entry.py is the actual 3dfef7420 fix copied read-only from its owner. Seven controls show only the unique typed checkpoint succeeds; generic error, ordinary early return, cleanup failure, nonlocal body return, nonlocal cleanup return and break all fail with code1. Cleanup was attempted and active0 in these mocks.

Run python3 reproduce_mock_controls.py; outputs go into runtime/ and assert the seven expected completion results. Committed actual result files remain unchanged. Native helper e19c5fd987 cleanup semantics were independently read; actual native PG qualification belongs to /root/pg_birth and is not replaced by these controls.
