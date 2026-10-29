Actual KV weighted-clock and CA arithmetic NUMBER check

PASS: own clock recurrence uses the real kit_c cell netlist, aliases and raw
source-rise/source-fall T/N/F/M arrivals. Per-cell incoming delay is weighted by
that master's published factor and the actual local input polarity, independently
of clock_components.py. Expected results match the implementation on all1920taps
and15424nodes percorner within6.4e-12ps. All15296physicalcells traced:15207inverters
and89BUFx24;7184source-rise local inputs/8112source-fall. Raw arrival and component
sums reproduce, no negative increments. Both-edge duty ranges TT48.15..51.81%,
FF47.95..51.09%.

PASS:3595 K/DEPTH/schedule identities,140region tree coverage,139nominal start
sampling steps, TT/FF139measured-edge sampling arithmetic. Sampling distances
minimum76.23/58.03ps >=26.5; zero missing/unbound. Min low margins104.733/109.333,
min high515.865/516.265 reproduce reported rows within0.067ps rounding. Bind833ps
versus gate833.333ps exposed in report; unchanged source, no clock relaxation.

Scope: calibrated factors are previously published inputs, not a new independent
transistor characterization. Margin and sampling arithmetic uses the reported
OCV intervals, not an independent full-pair OCV/droop solve. Existing conservative
glue FF real-view -50.98 remains FAIL. No freeze or signoff claim.

Canonical run intel1 scratch2/claude/codex-number-kv-clock-1029; all input owner
artifacts read-only. check.py is standalone except its comparison-target import.
