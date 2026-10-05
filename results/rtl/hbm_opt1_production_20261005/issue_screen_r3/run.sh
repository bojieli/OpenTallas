#!/bin/bash
set -u
J=/srv/opentallas/jobs-overflow/euclid-hbm-opt1-issue-screen-r3
S=/srv/opentallas/jobs-overflow/euclid-hbm-opt1-issue-source-e3cbe9ada
ulimit -t unlimited; ulimit -v unlimited; ulimit -f unlimited
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 MAKEFLAGS=-j16 TMPDIR="$J/tmp"
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
cd "$S"
python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_issue_pq_sm_boundary \
 --source physical/hbm_opt1_production_20261005/ot_hbm_accel_issue_pq_sm_boundary.sv \
 --source rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_issue_pq.sv \
 --source rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv \
 --source rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv \
 --source rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv --source rtl/gpu/ot_gpu_issue.sv \
 --param ENABLE=1 --param PQ_ENABLE=1 \
 --clock-period-ns 0.833333333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.166666667 --core-input-delay-max-ns 0.473 \
 --output-delay-min-ns 0.166666667 --output-delay-max-ns 0.323 \
 --false-path-from rst_n --orfs-corner WC --hold-corners WC,BC \
 --stages pnr --core-utilization 30 --place-density 0.55 --hold-margin-ns 0.01 \
 --orfs-var ADDER_MAP_FILE= --orfs-var TMPDIR=/work/tmp --slew-margin-percent 30 --purpose characterization \
 --nickname-tag euclid_pq_issue_s1_e3c_r3 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$J/work" --output "$J/physical.json" --force > "$J/route.log" 2>&1
rc=$?; printf '%s\n' "$rc" > "$J/route.exit"
if test -n "$(find "$J/work/orfs/results" -name 6_final.odb -print -quit 2>/dev/null)"; then
 python3 tools/w18/corner_sta.py --orfs-dir "$J/work/orfs" --output "$J/corner_sta.json" > "$J/corner.log" 2>&1
 printf '%s\n' "$?" > "$J/corner.exit"
else
 printf 'No final ODB; no signoff corner claim\n' > "$J/corner_not_run.txt"
fi
git status --porcelain > "$J/source.postdirty"
printf '%s\n' "$rc" > "$J/exit"
