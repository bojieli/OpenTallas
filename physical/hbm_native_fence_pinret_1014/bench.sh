#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); mut=${2:-0}; seed=${3:-7}
mkdir -p "$out"
cd "$(dirname "$0")"
python3 - <<'PY'
import hashlib,json,pathlib
m=json.loads(pathlib.Path('source_manifest.json').read_text())
for f in m['files']:
 p=pathlib.Path(f['source']).name
 assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==f['successor_sha256'],p
PY
iverilog -g2012 -Ptb_fence_pinret.MUT="$mut" -Ptb_fence_pinret.SEED="$seed" -Ptb_fence_pinret.INPIN=1 -Ptb_fence_pinret.HOLDBUF=2 -o "$out/fence.vvp" -s tb_fence_pinret tb_fence_pinret.sv ot_gpu_rf_visibility_fence_p2.sv ot_fence_pin_return.sv ot_sc_pfifo.sv ot_gpu_rf_visibility_fence.sv ot_s81_head_min_delay.sv ot_hdc_delay.sv min_delay_cells_model.sv
sim_rc=0
vvp -n "$out/fence.vvp" > "$out/simulation.log" 2>&1 || sim_rc=$?
cat "$out/simulation.log"
test "$sim_rc" = 0
grep -q '^FENCE_P PASS .*bad=0$' "$out/simulation.log"
