# Exponential-only service validation

`before_engine.sv` and `before_softmax.sv` are launch snapshots. `workspace_engine.sv`
is the measured candidate, including pre-existing uncommitted divisor tuning.
`committed_engine.sv` is the task-only engine change validated in the default full
4,200-case campaign; earlier workspace edits remain unstaged.

`tb_exp_only.sv` is the existing HC transcendental bench with only
`ENABLE_SIGMOID=0` added. `cases.hex` copies the 4,200 authoritative vectors from
`testdata/rtl/a3_hc_transcendental/cases.hex`, replacing the expected result/error
for each operation-1 request with zero/ERR_ARGUMENT (1). Operation-0 vectors are
unchanged. Both campaigns include active reset and output backpressure.

Protocol regression: `python3 -m pytest -q tests/test_softmax_exp_reuse.py tests/test_softmax_lane_write.py`.
Numerical softmax and containing attention use existing reference vectors;
source inventories and measured logs accompany this report. The specialized
engine refuses unsupported sigmoid at acceptance, before zero/large-argument
fast paths, and the default ENABLE_SIGMOID=1 preserves full functionality.
