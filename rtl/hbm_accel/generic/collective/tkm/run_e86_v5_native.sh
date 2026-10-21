#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
python3 tools/run_abi3_physical.py --view asap7 --top ot_hgi_coll_tkm_tile_e86_v5 \
 --source rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv \
 --source rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_tile_e86_v5.sv \
 --clock-port clk --clock-period-ns 0.770 --stages synth \
 --synth-timeout-seconds unlimited --keep-workdir "$OUT/work" --force --output "$OUT/synthesis.json" > "$OUT/synthesis.stdout.log" 2>&1
python3 - "$OUT" <<'PY'
import sys,subprocess,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools');import run_abi3_physical as ABI
out=Path(sys.argv[1]);libs=ABI.VIEWS['asap7']['corners']['TT']['liberty']
cmd=[sys.executable,'tools/ref_tile/native_census.py','--netlist',str(out/'work/mapped.v'),'--top','ot_hgi_coll_tkm_tile_e86_v5','--kit','hcoll_v7_tkm_tile_e86v5','--out',str(out/'native_census.json')]
for p in libs:cmd.extend(['--liberty',str(p)])
(out/'native_command.json').write_text(json.dumps({'command':cmd,'scope':'required pre-layout synthesis/native qualification only, not ORFS mapped gate or physical timing pass'},indent=1)+'\n')
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/'native.stdout.log').write_text(r.stdout);print(r.stdout);sys.exit(r.returncode)
PY
