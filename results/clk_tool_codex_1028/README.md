# Clock stage wire-stack correction

The built-in BUFx24 ladder coefficients in die_trial.STAGE_1X_TT were
measured on 1x M8/M9 wires (DIE-QC-3 cal1x). The stage registry incorrectly
keyed that entry as `clock_rc: ndr`, allowing a BUFx24 NDR DME request to
pass the stack check with the wrong wire model. Its key now says `1x`.
No coefficients, clock builds, die plans or sign-off thresholds change.
None of the current five die configs selects this entry; historical
inverter replays remain explicitly legacy and retain their failed stage check.

Focused checks: 5 PASS (wrong-stack/polarity/corner/tamper and build refusal).
The added control demonstrates that an otherwise identical BUFx24 NDR
request is rejected while its actual 1x stack is accepted.

Inherited clock replays remain live on intel2 (`clktool1-hbm`,
`clktool3-qc25`) and epyc2 (`clktool3-s81go16`); no duplicate builds started.

The future s81_go16 config now uses 24 independent DME workers, matching
the existing QC configuration. The inherited serial replay continues
untouched. DME attaches regions in the same serial order; existing
serial/parallel equality and config/argv checks: 17 PASS. This avoids
unnecessarily serial region solves on future clock builds; CLI --workers
still overrides it to match admitted resources. No RTL or cycle change.

Actual clock reach now has an opt-in post-legalisation check:
`die_trial.py kit ... --rep-actual-max 450` writes actual_reach.json and
refuses to publish tree.json when actual parent_of/sites cell hops or
final tap stubs exceed the supplied limit (or coordinates are missing).
Default is off and unchanged. Any later overlay must re-run
`python3 tools/die_plan/clock_reach.py FINAL_TREE --max-um 450 --json NEW_RECORD`.
Existing records are never overwritten. This checks existing 12.1e reach,
not ideal topology nodes or delay-model spans. The native final parity
restorer is used as the final tap driver when present.

Retained S81 go16 reproduces the independent geometry failure exactly:
42,328 cell edges +8,501 tap stubs, 8 over450, worst653.4um (bk_sel),
seven others457.38um; no missing sites. S81 owner's structural reach17
candidate: 42,350 cell edges +8,501 stubs, zero over450, worst403.272um.
These are geometry results, not a route/timing pass. 14 focused tests PASS
(actual-site mutation, missing coordinates, tap/polarity driver, exact
boundary and existing inverter/cell-path tests). No new P&R/STA launched.
