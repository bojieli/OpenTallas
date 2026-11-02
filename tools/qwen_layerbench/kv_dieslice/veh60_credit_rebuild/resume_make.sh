#!/bin/bash
# Resume a successful top Verilation without rerunning Verilator or children.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$D/b"
python3 "$D/guard_cache.py" pre
python3 - "$D" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
d=Path(sys.argv[1]);o=d/'b/obj'
assert 'Exit status: 0' in (d/'top_generate.log').read_text()
assert not (o/'Vtb_kvslice_hier.mk').exists(), 'refuse to overwrite include'
original=Path('/srv/opentallas-scratch2/claude/codex-kv-veh60-gen1-1131/b/obj/Vtb_kvslice_hier.mk')
text=original.read_text()
block=re.search(r'VM_HIER_LIBS := \\\n(.*?)(?=\nhier_build:)',text,re.S).group(1)
old=re.findall(r'\bV[^\s\\]+\.a\b',block)
libs=json.loads((d/'child_libs.json').read_text())
assert old==libs and len(libs)==51,(len(old),len(libs))
assert all((o/f).is_file() for f in libs)
include='# Private cache-only hierarchy: no regeneration or child recipes.\nVM_HIER_LIBS := '+' '.join(libs)+'\n'
(o/'Vtb_kvslice_hier.mk').write_text(include)
files=sorted(p for p in o.iterdir() if p.is_file() and p.suffix in ('.cpp','.h','.mk','.dat'))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(d/'resume_generated_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PRIVATE_HIERARCHY_MANIFEST_PASS',len(libs),'libraries',len(files),'generated files')
PY
mapfile -t LIBS < <(python3 -c 'import json,sys;print("\n".join(json.load(open(sys.argv[1]))))' "$D/child_libs.json")
OLDS=();for lib in "${LIBS[@]}";do OLDS+=(-o "$lib");done
make -n -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 Vtb_kvslice > "$D/top_make_plan.log"
python3 "$D/guard_cache.py" make-plan
if grep -Eq '(^|[[:space:]])([^[:space:]]*/)?verilator(_bin)?([[:space:]]|$)|hier_launch|hierarchical-child' "$D/top_make_plan.log";then
  echo 'Unexpected Verilator generation in make plan' >&2;exit 1
fi
/usr/bin/time -v make -C obj -f Vtb_kvslice.mk "${OLDS[@]}" -j8 Vtb_kvslice > "$D/top_make.log" 2>&1
python3 "$D/guard_cache.py" post
python3 - "$D" <<'PY'
import hashlib,json,sys
from pathlib import Path
d=Path(sys.argv[1]);m=json.loads((d/'resume_generated_sha256.json').read_text())
for name,sha in m.items():
 assert hashlib.sha256((d/'b/obj'/name).read_bytes()).hexdigest()==sha,name
print('GENERATED_TOP_UNCHANGED_PASS',len(m))
PY
sha256sum obj/Vtb_kvslice > "$D/binary.sha256"
printf 'BUILD_ONLY_COMPLETE no_simulation_run\n' > "$D/status"
