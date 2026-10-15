#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
root=${HCOLL_ROOT:?source root}
mkdir -p "$out"
for spec in 11:16 10:15;do
 ns=${spec%:*};nd=${spec#*:};stem="ns${ns}_nd${nd}"
 yosys -Q -T -p "read_verilog -sv $root/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_qslots.sv; hierarchy -top ot_hgi_coll_qslots_output -chparam NS $ns -chparam ND $nd; proc; opt; write_json $out/$stem.json; stat" > "$out/$stem.log"
done
python3 - "$out" <<'PY'
import json,pathlib,sys
out=pathlib.Path(sys.argv[1]);counts={}
for p in out.glob('ns*.json'):
 m=json.loads(p.read_text())['modules']['ot_hgi_coll_qslots_output']
 cells=m['cells'];n=0
 for c in cells.values():
  if 'dff' in c['type'].lower():n+=len(c['connections']['Q'])
 counts[p.stem]={'synthesized_register_bits':n,'clock_root_limit':15000,'pass':n<=15000}
assert all(x['pass'] for x in counts.values())
(out/'clock_root_counts.json').write_text(json.dumps(counts,indent=2)+'\n')
print(json.dumps(counts))
PY
