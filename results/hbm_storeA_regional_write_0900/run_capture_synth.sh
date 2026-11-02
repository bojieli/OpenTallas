#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
yosys -p 'read_verilog -sv ot_hgi_sfu_store_a_regional_capture.sv; hierarchy -top ot_hgi_sfu_store_a_regional_capture; proc; opt; stat; write_json capture_mapped.json' > capture_synth.log 2>&1
python3 - <<'PY'
import json
x=json.load(open('capture_mapped.json'))['modules']['ot_hgi_sfu_store_a_regional_capture']
ff={n:c for n,c in x['cells'].items() if c['type'] in ['$adff','$dff']}
count=sum(len(c['connections']['Q']) for c in ff.values())
r={'FFbits_after_normal_proc_opt':count,'FFvector_cells':len(ff),'masters':sorted({c['type'] for c in ff.values()}),'physical_replication_retained':count==8800}
json.dump(r,open('capture_synth_summary.json','w'),indent=1);print(r)
assert count==8800,'same-D regional copies merged: source physical copy intent not preserved'
PY
