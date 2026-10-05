#!/usr/bin/env bash
set -u
source ~/.opentallas-env
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
export TMPDIR=/srv/opentallas-scratch2/codex/boole-w2-caller-sizing-20261005-r1/tmp
mkdir -p "$TMPDIR"
cd /srv/opentallas-scratch2/codex/boole-w2-caller-a80299374
job=/srv/opentallas-scratch2/codex/boole-w2-caller-sizing-20261005-r1
git rev-parse HEAD > "$job/source.sha"
/srv/opentallas-scratch/admit.sh 8 -- python3 -u tools/run_abi3_physical.py \
 --view asap7 --corner ss --top ot_hbm_accel_w2_caller_cut --param PACK_W2=1 \
 --source rtl/hbm_accel/physical/w2_20261005/ot_hbm_accel_w2_caller_cut.sv \
 --source rtl/hbm_accel/sm/wavepack_20261005/ot_hbm_accel_w2_pair_request_join.sv \
 --source rtl/hbm_accel/sm/wavepack_20261005/ot_hbm_accel_w2_result_join.sv \
 --source rtl/hbm_accel/sm/wavepack_20261005/ot_hbm_accel_w2_address_hook.sv \
 --clock-period-ns 0.833333333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --stages synth --purpose characterization \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$job/work" --output "$job/synthesis.json"
rc=$?
echo "$rc" > "$job/exit"
exit "$rc"
