#!/usr/bin/env bash
# Stage generated nominal/old-role transport wrappers. Run coupon/run.sh via ot-run.
set -euo pipefail
R=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
P=$(realpath "${1:?selected HEAD plan}")
O=$(realpath -m "${2:?fresh output directory}")
[ ! -e "$O" ] || { echo "fresh output required" >&2; exit 2; }
mkdir -p "$O"
python3 - "$P" "$O" <<'PY'
import json,sys,os
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text());o=Path(sys.argv[2]);names=['hd_st_k5','hd_spn_end','hd_serdes']
(o/'leaf_sources.f').write_text('\n'.join(sorted({f for n in names for f in p['partition_types'][n].get('sources',[])}))+'\n')
# Preserve the same geometry, latencies, ordinary type roles and leaf implementation.
for t in p['partition_types'].values():
 t.get('reset',{}).pop('bootstrap_buses',None);t.get('reset',{}).pop('bootstrap_contents',None)
 for c in t.get('hard_cores',[]):
  if c.get('pins_file'):
   pin=(Path(sys.argv[1]).parent/c['pins_file']).resolve()
   c['pins_file']=os.path.relpath(pin,o)
(o/'old_roles_mutant.json').write_text(json.dumps(p)+'\n')
PY
python3 "$R/tools/die_plan/gen.py" rtl "$P" --types hd_st_k5,hd_spn_end,hd_serdes --rtl-root "$R" --out "$O/nominal" > "$O/gen_nominal.log" 2>&1
python3 "$R/tools/die_plan/gen.py" rtl "$O/old_roles_mutant.json" --types hd_st_k5,hd_spn_end,hd_serdes --rtl-root "$R" --out "$O/old" > "$O/gen_old.log" 2>&1
python3 "$R/tools/s81_head/head_transport_coupon.py" --repo "$R" --generated-root "$O" --out "$O/coupon"
