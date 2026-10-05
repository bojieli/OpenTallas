#!/bin/bash
set -uo pipefail
source ~/.opentallas-env
cd /srv/opentallas/repos/peirce-topk-balanced-fanout-5ee4cde5b
export OT_ORFS_NUM_CORES=16
export NUM_CORES=16
export MAKEFLAGS=-j16
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OT_SYNTH_TIMEOUT_SECONDS=unlimited
export OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -f unlimited
JOB=/srv/opentallas-scratch/jobs/peirce-topk-balanced-u25-r1
python3 tools/run_abi3_physical.py --view asap7 --top ot_gpu_router_topk_ip_bal_ctx384 --source rtl/gpu/ot_gpu_router_topk.sv --source rtl/gpu/ot_gpu_router_topk_ip_bal.sv --source rtl/gpu/ot_gpu_topk_compare_bal.sv --source rtl/gpu/ot_gpu_router_topk_ip_bal_ctx384.sv --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr --die-area 0 0 317.882162 317.856392 --core-area 2.052 2.16 315.864162 315.676392 --core-utilization 25 --place-density 0.55 --hold-margin-ns 0.02 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag peirce_ctl_topk_bal_u25_r1 --keep-workdir "$JOB/work" --output "$JOB/physical.json" > "$JOB/route.log" 2>&1
rc=$?
echo "route_rc=$rc" > "$JOB/exit"
if [ "$rc" != 0 ]; then exit "$rc"; fi
python3 tools/w18/corner_sta.py --orfs-dir "$JOB/work/orfs" --output "$JOB/corner_sta.json" > "$JOB/corner.log" 2>&1
rc=$?
echo "corner_rc=$rc" >> "$JOB/exit"
exit "$rc"
