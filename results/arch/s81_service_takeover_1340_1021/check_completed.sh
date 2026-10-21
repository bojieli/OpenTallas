#!/bin/bash
set -u
ROOT=/srv/opentallas-scratch/claude/elemsvc-g4-1021
sha256sum tools/ref_tile/native_census.py tools/textbook_lint.py > out/checker_identity.sha256
for variant in sram norst; do
 old=$ROOT/out_$variant
 args=();for l in "$old"/map/lib/*.lib;do args+=(--liberty "$l");done
 sha256sum "$old/map/flat.v" "$old"/map/lib/*.lib > "out/${variant}_identity.sha256"
 python3 tools/ref_tile/native_census.py --netlist "$old/map/flat.v" --top dsdv_svc_att --out "out/${variant}_census.json" "${args[@]}" > "out/${variant}_census.log" 2>&1
 code=$?;echo "CHECKER_VARIANT=$variant EXIT=$code"
 python3 - "$variant" "out/${variant}_census.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[2]));v=r.get('violations',[])
print(sys.argv[1],r.get('status'),r.get('max_dynamic_loads'),len(v),'roles',len(r.get('role_errors',[])))
print([{k:x.get(k)for k in ['driver','net','loads']}for x in sorted(v,key=lambda x:x['loads'],reverse=True)[:12]])
PY
done
