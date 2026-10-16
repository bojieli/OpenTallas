Native CTS kit new-intake guard (2026-10-15)

Actual old pa5 source e2333e464 fails all three SDC checks; its corrected,
otherwise unchanged successor bf6c182bf passes. retained_case.json records
immutable source-blob replay, not a route or qualification claim.

Only CE.native_leaf modes are checked: multiple_cts_roots and tile
hybrid_entries. Their schema prohibits custom SDC hooks. Complete generated
SDC byte comparison binds the stage flags, actual Tcl procedure, invocation,
and subsequent commands, rejecting operational changes despite retained
markers. This intentionally requires current generated native SDCs, rather
than attempting to prove arbitrary edited Tcl equivalent. Single-root tiles
and legacy parent entry policy are exempt. VM control d437a9c0a independently
regenerated four single-root kits byte-identically on 4af.

Run: python3 -m unittest discover -s tools/ref_tile/tests -p test_gate_native_cts_sdc.py -v
6 tests pass, including current multiple/hybrid positive, each old SDC,
seven executable tamper mutations, missing SDC, ordinary/legacy controls,
and the actionable local gate failure. Existing stale multi-root deferral
suite: 2 tests pass. Numeric constraints and generator behavior unchanged.

The check runs in check_kit, already used by local gate and submit_check.
closure_loop calls ref_gate_at_submit only during new ingest and only if
QUEUED after earlier checks. No daemon, retry, collect, or frozen runtime
path is edited; accepted jobs and CLOSED evidence remain untouched.

Refusal path: rebase onto main; run python3 tools/ref_tile/ref_tile.py gen
<exact spec.json>; review RTL/pins/periods remain as intended; commit generated
kit; run a fresh source-bound --cts gate; submit a new normal successor.
Do not edit frozen originals or reuse an old gate under a different source.
