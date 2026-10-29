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
