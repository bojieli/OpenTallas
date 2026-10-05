#!/usr/bin/env bash
# Owner-directed distinct geometries of the already exact selected endpoint.
set -euo pipefail
[[ $# = 3 ]] || { echo 'usage: VARIANT(ctx-u12|ctx-u15|die-u12) FRESH_OUTPUT LABEL' >&2; exit 2; }
variant=$1; out=$2; label=$3
[[ "$out" = /* && ! -e "$out" && "$label" =~ ^[a-zA-Z0-9_-]+$ ]]
cd "$(git rev-parse --show-toplevel)"
[[ -z "$(git status --porcelain)" ]]
case "$variant" in
 ctx-u12) top=noc_tw_coll_ctx_f12_txmask; util=12 ;;
 ctx-u15) top=noc_tw_coll_ctx_f12_txmask; util=15 ;;
 die-u12) top=noc_tw_coll_die_f12_txmask; util=12 ;;
 *) exit 2 ;;
esac
mkdir -p "$out"
git rev-parse HEAD > "$out/source.sha"
printf '%s\n' "$variant" > "$out/variant"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical_aligned_guarded.py \
 --macro-track-gate --view asap7 --top "$top" --param TX_MASK_LA=1 \
 --source rtl/link/ot_link_afifo.sv \
 --source rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
 --source rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
 --source rtl/gpu_sys/ot_gpu_coll_endpoint_f12_txmask.sv \
 --source "results/rtl/hbm_accel_fmax_inventory_20261004/noc/wrappers/$top.sv" \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
 --stages synth,pnr --core-utilization "$util" --place-density 0.55 \
 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose signoff_target --nickname-tag "$label" \
 --keep-workdir "$out/work" --output "$out/physical.json" > "$out/run.log" 2>&1
python3 tools/w18/corner_sta.py --orfs-dir "$out/work/orfs" --output "$out/corner_sta.json" > "$out/corner.log" 2>&1
