S81 relay/delay parameterized leaf interfaces

The S81 source manifest now specializes `ot_s81_rly`, `ot_s81_rly_k`,
`ot_hdc_delay`, and `ot_hdc_v41x_dly` before Slang blackboxes their bodies.
Slang's empty blackbox importer otherwise reuses the first instance's interface
rather than evaluating distinct W/D/RESET/RSREG interface values. This caused 9,492 relay input pad ties
and the VP W=1 valid delay to import as W=4 in strict-bind v10.

`run.py --out <new-directory>` elaborates the actual repository masters in nine
small instances and checks every intended width and parameter. Result: PASS9.
`--omit-specialization` is the negative control: it fails on relay r66 (imported
width1 instead of66). The gate ran through ot-run on epyc2 in
`/srv/opentallas-scratch2/claude/codex-ds-abi-2148`, units4072492 and4086606.
The script-only setup failures in gate/ and gate2/ are retained in that run root;
they were duplicate fixture instance/output names and an assertion decoding
already-decoded decimal parameters, respectively.

Private RTL is unchanged. No pipeline stage is added. Per-instance delay values
are restored to their authored values; comparison with the prior collapsed
bound graph is still required before using its timing in a token schedule.
The full source ELAB/strict-bind diagnostic is running under full/ in that run
root. This component gate is not a full strict-bind or token pass.

Followup: source/census inspection found ten more affected instantiated masters.
`prior_census.json` records their v10 interfaces. Its `params` field contains module parameter defaults,
which are empty for ordinary blackboxes; it does not count cell overrides.
The positive fixture checks both evaluated widths and explicit cell parameters.
Reset/landing/MU widths share one imported shape in the prior graph. The manifest also specializes these ten masters.
`transport_run.py` checks twenty actual-master instances, every port dimension,
and every explicit parameter: PASS20. Omitting specialization is caught at
chunk-w input width1 instead280. These restore evaluated interface semantics without
adding pipeline stages. The legacy collapsed graph cannot be a token oracle.

Correction to the initial census interpretation: module defaults being empty
never established that cell overrides were absent. `prior_cell_parameters.json`
confirms the old graph preserved service face masks, pad N values, delay D and
RESET values, and each relay W override. The defect is the imported shared port
shape: for example a W=1 relay cell refers to the module whose i/o ports are
W=276. The fix evaluates the interface at each instance's existing parameters;
it does not repair an observed lost-N schedule defect. Pad/valid-delay/reset
specialization additionally makes that contract explicit.
