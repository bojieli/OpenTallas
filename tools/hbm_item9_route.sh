#!/usr/bin/env bash
# Source-ready characterization of full NL128 mux/endpoint; all IO timed.
# The actual enclosing allocation and macroloads remain a distinct mandatory gate.
set -euo pipefail
[[ $# = 4 ]] || { echo 'usage: FRESH_OUTPUT UNIQUE_LABEL EXACT_ENDPOINT_RESULT EXACT_MUX_RESULT' >&2; exit 2; }
out=$1; label=$2; exact=$3; mux_exact=$4
[[ "$out" = /* && ! -e "$out" && "$label" =~ ^[a-zA-Z0-9_-]+$ ]]
cd "$(git rev-parse --show-toplevel)"
[[ -z "$(git status --porcelain)" ]]
python3 - "$exact" "$mux_exact" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r['verdict']=='PASS_FULLSHAPE_ENDPOINT_EXACT'
assert r['added_cycles_per_collective']==0 and r['added_cycles_per_record']==0
for f in ('rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv',):
    assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==r['source_sha256'][f]
m=json.loads(Path(sys.argv[2]).read_text())
assert m['verdict']=='PASS_FULLSHAPE_MUX_EXACT' and m['added_mux_cycles']==0
for f in ('rtl/gpu_sys/ot_gpu_coll_mux_f12.sv','rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv'):
    assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==m['source_sha256'][f]
PY
mkdir -p "$out"
git rev-parse HEAD > "$out/source.sha"
cp "$exact" "$out/exact_endpoint.json"
cp "$mux_exact" "$out/exact_mux.json"
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical_aligned_guarded.py \
 --macro-track-gate --view asap7 --top noc_tw_coll_ctx_owner64 \
 --param TX_MASK_LA=1 --param OWNER64=1 --param RXOH=1 --param RDUP=16 \
 --source rtl/link/ot_link_afifo.sv --source rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
 --source rtl/gpu_sys/ot_gpu_coll_mux_f12.sv --source rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv \
 --source rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv \
 --source results/rtl/hbm_item9_closure_20261005/noc_tw_coll_ctx_owner64.sv \
 --clock-period-ns .833 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 \
 --die-area 0 0 540 540 --core-area 2.16 2.16 538.84 538.84 \
 --stages synth,pnr --core-utilization 30 --place-density .55 \
 --hold-margin-ns .01 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose signoff_target --nickname-tag "$label" \
 --keep-workdir "$out/work" --output "$out/physical.json" > "$out/run.log" 2>&1
python3 tools/w18/corner_sta.py --orfs-dir "$out/work/orfs" --output "$out/corner_sta.json" > "$out/corner.log" 2>&1
