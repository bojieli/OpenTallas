#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
python3 tools/hbm_layer_vehicle/topk_hub_fixture_2000.py inputs gsc_layouts.json "$OUT/fixtures" > "$OUT/prepare.log" 2>&1
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,'tools/hbm_die_v15')
import master_filelist as M
out=Path(sys.argv[1]);root=Path('.').resolve()
prefer=[]
for f in ['rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv','rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static_glue.sv']:
 prefer.append(f)
files=[];manifests=[]
for top in ['ot_hbm_idx_rootctl_static_am','ot_hbm_idx_topk_static_f32','hfd_hgi_vms_glue_sw_t','hfd_vms_bank_native_q0_faces']:
 r=M.resolve(root,top,prefer=prefer)
 manifests.append(r)
 if r['unresolved'] or r['ambiguous']:raise RuntimeError(r)
 for f in r['files']:
  if f not in files:files.append(f)
 for macro in r['macros']:
  f=macro['file'].replace('_bb.v','.v')
  if not Path(f).exists():raise RuntimeError('actual SRAM model missing '+f)
  if f not in files:files.append(f)
(out/'source_closure.json').write_text(json.dumps(manifests,indent=2)+'\n')
(out/'files.f').write_text('\n'.join(files)+'\n')
PY
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version > "$OUT/verilator.version"
"$VL" --binary --timing -j 2 -Wno-fatal --top-module tb_topk_native_commit -Mdir "$OUT/obj" \
 -f "$OUT/files.f" rtl/test/hbm_topk_native_commit_2000/tb_topk_native_commit.sv > "$OUT/build.log" 2>&1
for mut in 0 1 2 3;do
 set +e
 "$OUT/obj/Vtb_topk_native_commit" "+DIR=$OUT/fixtures" "+MUT=$mut" > "$OUT/run$mut.log" 2>&1
 status=$?
 set -e
 printf '%s\n' "$status" > "$OUT/run$mut.exit"
 if [[ $mut == 0 ]];then test "$status" = 0;grep -q 'TOPK_NATIVE_COMMIT PASS' "$OUT/run$mut.log"
 else test "$status" != 0;grep -q 'TOPK_NATIVE_COMMIT FAIL' "$OUT/run$mut.log";fi
 tail -3 "$OUT/run$mut.log"
done
python3 - "$OUT" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);files=p.joinpath('files.f').read_text().splitlines()+['rtl/test/hbm_topk_native_commit_2000/tb_topk_native_commit.sv','tools/hbm_layer_vehicle/topk_hub_fixture_2000.py','tools/hbm_layer_vehicle/run_topk_native_commit_2000.sh']
p.joinpath('source.sha256.json').write_text(json.dumps({f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},indent=2)+'\n')
PY
