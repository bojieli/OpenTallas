# Verification-only identity and verdict controls

`identity_verdict.py` is a standalone source-owned request ledger, not a DUT
repair or an integration PASS. The caller supplies the independently validated
source/relay authority tag. `trace_on` is raw metadata only. Unknown startup
records are retained but cannot allocate a request or advance retirement.

Programme identities contain epoch, layer, position and token. Only actual
acceptance (`accept`, with explicit `monitors_known=True`) and a successful
actual source run (`run`, with explicit `run_ok=True`) establish ownership.
Each successful STATUS must match an active identity after actual source
completion and its complete, ordered RESULT bitmap. Unknown identities have no
fallback. An error STATUS terminates its owned request but records an application
error and cannot increase successful retirement. `finish()` checks actual
programme execution as well as exactly one successful completion per entry.
Explicit `require_retire=False` allows an intentionally partial smoke to require
actual programme acceptance/run without claiming retirement; observed STATUS
records still obey every identity, RESULT and source-completion check.

The integration must call observation checks at every authoritative consumer
sample, including the first sample, idle, and repeat reset. There is deliberately
no ledger reset or error-clear operation. Real reset cancellation needs an
explicit source-owned contract; it is not implemented here. Clock/NBA knowledge
propagation, source aliases, payload extraction, accepted identity binding and
source completion extraction remain the integrating harness's responsibility.
This Python ledger does not demonstrate startup safety of the DUT itself.

`kva_identity_scoreboard.sv` implements the same verification ledger for direct
bench integration. `expected_ids` is a constant packed programme map. The caller
packs the full identity into `ID_W` bits and supplies actual source events at
`sample_clk` after DUT NBA. `REQUIRE_RETIRE=0` selects explicit partial mode.
Before the guard's own source-reset authority, the integrating harness must
retain raw acceptance observations while withholding arbitrary startup events;
after that frontier, an acceptance with any required monitor unknown is an
error. The module rejects unknown acceptance valid and never clears errors.

`tb_identity_scoreboard.sv` directly exercises the reusable module. Fleet
`run_controls.py` runs Python controls, 13 four-state Icarus component cases,
then three real-module mutants. Committed `*.fail.log` files retain nonzero
failure witnesses. This is component validation, not full G7 integration.

`parse_verdict(log, returncode)` independently requires process rc0 and exactly
one `SMOKE_PASS` token with no `SMOKE_FAIL` token. Missing, repeated or conflicting
verdicts fail. CLI: `python3 identity_verdict.py LOG --returncode RC`.

`test_identity_verdict.py` includes startup, first-known idle malformed STATUS,
unknown valid, exact identity fields, wrong/order/duplicate RESULT, early STATUS,
error STATUS, missing execution and strict verdict controls. Three deliberate
mutants exercise the required independent oracles: removing startup authority
mutates the error ledger; masking to trace_on hides a required error; fallback
retires a wrong identity. Their witness lines are in `controls.log`.

Run on the fleet: `python3 -m unittest -v test_identity_verdict.py` from this
directory. Original vehicle failure evidence remains untouched. No schedule,
deadline, RTL or full vehicle was changed or rerun.

The exact module and bench also pass 11 two-state cases and all three real
mutants on fleet Verilator 5.050. Cases 7 and 12 require X and remain covered
by four-state Icarus. See `receipt.json`, `verilator_controls.log` and
`verilator_*.fail.log`. No unknown-state claim derives from Verilator.
