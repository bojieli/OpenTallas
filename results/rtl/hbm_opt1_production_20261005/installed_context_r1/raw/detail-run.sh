#!/bin/bash
set -eu
J=/srv/opentallas/jobs-overflow/euclid-opt1-installed-context-20261005-r1
S=/srv/opentallas-scratch/claude/hbm-fmax-sm/src
W=/srv/opentallas-scratch/claude/hbm-fmax-sm/routes/sm_r2/work/orfs
B=$W/results/asap7/opentallas_ot_hbm_accel_sm_v_asap7_fsm_sm_r2/base
ulimit -t unlimited; ulimit -v unlimited; ulimit -f unlimited
export NUM_CORES=1
sha256sum "$B/4_cts.odb" "$B/4_cts.sdc" "$B/1_2_yosys.v" "$S/rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv" "$S"/physical/hbm_accel_sm_views/*/*_ss.lib "$S"/physical/hbm_accel_sm_views/*/*_ff.lib > "$J/detail.pins.before"
set +e
for corner in ss ff; do
/srv/opentallas-scratch/admit.sh 8 -- docker run --rm --name "euclid-opt1-context-detail-$corner" -e NUM_CORES=1 -v "$J:/query" -v "$W:/retained:ro" -v "$S:/src:ro" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads 1 -no_init -exit /query/detail_$corner.tcl" > "$J/detail_$corner.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$J/detail_$corner.exit"
done
set -e
sha256sum "$B/4_cts.odb" "$B/4_cts.sdc" "$B/1_2_yosys.v" "$S/rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv" "$S"/physical/hbm_accel_sm_views/*/*_ss.lib "$S"/physical/hbm_accel_sm_views/*/*_ff.lib > "$J/detail.pins.after"
printf '%s\n' "$rc" > "$J/detail.exit"
