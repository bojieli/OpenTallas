#!/usr/bin/env bash
# Actual source/capture cells, not a whole SM array. Preserve synthesis for context P&R.
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
cd "$(git rev-parse --show-toplevel)"
[[ -z "$(git status --porcelain)" ]]
python3 - <<'PY'
import hashlib,json
from pathlib import Path
r=json.loads(Path('results/rtl/hbm_item9_closure_20261005/TXCTRL_context32_exact_r1/result.json').read_text())
assert r['verdict']=='PASS_TXCTRL_ACTUAL32_GATHER' and r['new_cycles']==0
for f in ('rtl/gpu_sys/ot_gpu_coll_endpoint_item9_txctrl.sv','rtl/gpu_sys/ot_gpu_coll_item9_context32_txctrl.sv'):
 assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==r['source_sha256'][f]
PY
mkdir -p "$out"
git rev-parse HEAD > "$out/source.sha"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical.py \
 --view asap7 --top ot_gpu_coll_item9_context32_txctrl \
 --param ENABLE=1 --param NSM=32 --param NL=128 --param OWNER64=1 \
 --param TX_MASK_LA=1 --param RXOH=1 --param RDUP=16 --param TXCTRL=1 \
 --source rtl/gpu_sys/ot_gpu_reset_ctrl.sv --source rtl/link/ot_link_afifo.sv \
 --source rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv --source rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
 --source rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv \
 --source rtl/gpu_sys/ot_gpu_coll_endpoint_item9_txctrl.sv \
 --source rtl/gpu_sys/ot_gpu_coll_item9_context32_txctrl.sv \
 --clock-port clk_sm --ingress-clock-port clk_link \
 --core-input-port por_n --core-input-port issue --core-input-port issue_mode \
 --core-input-port issue_count --core-input-port issue_va \
 --ingress-input-port switch_rx_v --ingress-input-port switch_rx_rec \
 --ingress-input-delay-min-ns .1666 --ingress-input-delay-max-ns .1666 \
 --sdc-append results/rtl/hbm_item9_closure_20261005/context32_clocks.sdc \
 --clock-period-ns .833 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 \
 --stages synth \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose characterization --nickname-tag item9_loaded32_synth_r1 \
 --keep-workdir "$out/work" --output "$out/physical.json" > "$out/run.log" 2>&1
