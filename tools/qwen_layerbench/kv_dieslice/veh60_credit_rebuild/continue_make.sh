#!/bin/bash
# ROOT exception: make-only continuation after exact old scope termination.
# Normal96GB/8-thread admission permits policy-j3; never rerun Verilator.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$D/b"
python3 "$D/guard_cache.py" pre
python3 - "$D" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
d=Path(sys.argv[1]);o=d/'b/obj'
original=Path('/srv/opentallas-scratch2/claude/codex-kv-veh60-gen1-1131/b/obj/Vtb_kvslice_hier.mk')
block=re.search(r'VM_HIER_LIBS := \\\n(.*?)(?=\nhier_build:)',original.read_text(),re.S).group(1)
old=re.findall(r'\bV[^\s\\]+\.a\b',block)
libs=json.loads((d/'child_libs.json').read_text())
assert sorted(old)==sorted(libs) and len(old)==51
expected='# Private cache-only hierarchy: no regeneration or child recipes.\nVM_HIER_LIBS := '+' '.join(old)+'\n'
assert (o/'Vtb_kvslice_hier.mk').read_text()==expected
files=sorted(p for p in o.iterdir() if p.is_file() and p.suffix in ('.cpp','.h','.mk','.dat'))
(d/'continue_generated_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
objects=sorted(o.glob('*.o'))
(d/'continue_objects_before.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objects},indent=2)+'\n')
print('CONTINUE_CACHE_MANIFEST_PASS',len(libs),'libraries',len(files),'generated files',len(objects),'completed objects')
PY
mapfile -t LIBS < <(python3 -c 'import json,sys;print("\n".join(json.load(open(sys.argv[1]))))' "$D/child_libs.json")
OLDS=();for lib in "${LIBS[@]}";do OLDS+=(-o "$lib");done
make -n -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 Vtb_kvslice > "$D/top_make_plan.log"
python3 "$D/guard_cache.py" make-plan
if grep -Eq '(^|[[:space:]])([^[:space:]]*/)?verilator(_bin)?([[:space:]]|$)|hier_launch|hierarchical-child' "$D/top_make_plan.log";then
  echo 'Unexpected generation in make plan' >&2;exit 1
fi
/usr/bin/time -v make -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 Vtb_kvslice > "$D/continue_make.log" 2>&1
python3 "$D/guard_cache.py" post
python3 - "$D" <<'PY'
import hashlib,json,sys
from pathlib import Path
d=Path(sys.argv[1])
for manifest in ['continue_generated_sha256.json','continue_objects_before.json']:
 m=json.loads((d/manifest).read_text())
 for name,sha in m.items():
  assert hashlib.sha256((d/'b/obj'/name).read_bytes()).hexdigest()==sha,name
 print('CONTINUE_UNCHANGED_PASS',manifest,len(m))
PY
sha256sum obj/Vtb_kvslice > "$D/binary.sha256"
printf 'BUILD_ONLY_COMPLETE no_simulation_run\n' > "$D/status"
