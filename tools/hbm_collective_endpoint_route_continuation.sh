#!/usr/bin/env bash
# Explicit ONE full-size endpoint continuation, after the retained route verdict
# and a source-priced fix. Existing jobs are not watched, stopped, or retried.
# Run only on an admitted remote host, from the new clean source worktree.
set -euo pipefail
if [[ $# != 2 ]]; then
    echo "usage: $0 FRESH_ABSOLUTE_OUTPUT UNIQUE_LABEL" >&2
    exit 2
fi
out=$1
label=$2
[[ "$out" = /* && ! -e "$out" ]]
[[ "$label" =~ ^[a-zA-Z0-9_-]+$ ]]
root=$(git rev-parse --show-toplevel)
cd "$root"
[[ -z "$(git status --porcelain)" ]]
git merge-base --is-ancestor 1e5b6c651 HEAD
mkdir -p "$out"
git rev-parse HEAD > "$out/source.sha"
export OT_ORFS_NUM_CORES=16
export OT_SYNTH_TIMEOUT_SECONDS=unlimited
export OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
# 24GiB is the retained route's admission estimate, never a process/cgroup cap.
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical_aligned_guarded.py \
    --macro-track-gate --view asap7 --top noc_tw_coll_die_f12 \
    --source rtl/link/ot_link_afifo.sv \
    --source rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
    --source rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
    --source rtl/gpu_sys/ot_gpu_coll_endpoint_f12.sv \
    --source results/rtl/hbm_accel_fmax_inventory_20261004/noc/wrappers/noc_tw_coll_die_f12.sv \
    --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
    --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
    --stages synth,pnr --core-utilization 12 --place-density 0.55 \
    --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
    --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
    --purpose signoff_target --nickname-tag "$label" \
    --keep-workdir "$out/work" --output "$out/physical.json" > "$out/run.log" 2>&1
python3 tools/w18/corner_sta.py --orfs-dir "$out/work/orfs" \
    --output "$out/corner_sta.json" > "$out/corner.log" 2>&1
