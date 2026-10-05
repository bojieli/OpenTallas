#!/usr/bin/env bash
# Route the reduced five-way Qwen reduction/scale tile on an ORFS-capable host.
# The manifest pins exactly the RTL and tool inputs measured in the matched
# N1/N5 synthesis comparison. This run is a physical characterization only.
set -euo pipefail
cd "$(dirname "$0")/.."
manifest=configs/hardware/qwen_m5_reduce_route_manifest.json
output=results/physical_hdc/asap7/qwen_m5_reduce_g2w2_route/physical.json
python3 - "$manifest" <<'PY'
import hashlib, json, pathlib, sys
manifest=json.load(open(sys.argv[1]))
for name, expected in manifest['source_sha256'].items():
    got=hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()
    if got!=expected:
        raise SystemExit(f'stale route input {name}: expected {expected}, got {got}')
PY
python3 tools/run_abi3_physical.py \
  --view asap7 --top ot_hdc_qwen_m5_reduce_scale \
  --param G=2 --param W=2 --param N=5 \
  --source rtl/hdc/ot_hdc_qwen_m5_reduce_scale.sv \
  --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/hdc/ot_hdc_delay.sv \
  --source rtl/hdc/ot_hdc_sfu.sv \
  --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv \
  --clock-period-ns 0.92 --stages pnr --corner TT \
  --expected-not-met --core-utilization 15 --place-density 0.55 \
  --max-transition-ns --slew-margin-percent 60 \
  --nickname-tag qwen_m5_reduce_g2w2_route \
  --output "$output" "$@"
python3 - "$output" <<'PY'
import json, sys
record=json.load(open(sys.argv[1]))
assert record['flow_completed'] and 'pnr' in record['stages_completed']
assert record['design']['parameters']=={'G':2,'N':5,'W':2}
print('Routed record:', sys.argv[1])
print('Status:', record['status'], 'DRC:', record['design']['drc'],
      'antenna:', record['design']['antenna'], 'area_um2:', record['design']['area_um2'])
PY
