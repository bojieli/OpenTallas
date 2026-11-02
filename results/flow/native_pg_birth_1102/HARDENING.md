Peer-review hardening, 2026-11-02

The native C++ module and its ABI/artifact hash are unchanged. Tcl admission now
requires the begin-owned actually loaded module path; it refuses coroutines,
ensembles and TclOO objects as well as procs/aliases. Missing pinned-Tcl
corotype introspection fails closed. This is a controlled-source runtime
contract, not resistance to scripts replacing the interpreter's own guards.

Begin installs strict command guards itself and rolls back a partial execution
trace installation. Cleanup attempts every trace removal and native uninstall;
end/eval preserve the original operation/audit error when cleanup also fails.
The GRT adapter requires strict mode and emits an explicit whole-body driver
that cleans up failed PRE/body/POST hooks. Its receipt remains dispatch_ready
false until the actual owner launcher uses that driver or a reviewed equivalent.

26 targeted source tests pass, including actual Tcl coroutine/ensemble/object
negative controls, partial trace setup/removal failures and original-error
preservation. A tiny pinned-runtime query passed: native status/audit commands
are correctly classified by corotype and are neither ensembles nor objects;
inactive native callback refuses admission.

The first loaded-input begin smoke correctly refused the planned LLfd 3_place
before callback installation:790 open PG terms/17802 checked. No CTS/STA/GRT
ran. Raw source SHA6962c6d7... remains unchanged; guarded saved-copy PG closure
is required before that sole proposed CTS canary. This is an input PG defect,
not an extension failure. Failed harness/log remains under Intel2 owned
codex-pg-birth-cts-0219/hardening_0242/begin_smoke.log.
