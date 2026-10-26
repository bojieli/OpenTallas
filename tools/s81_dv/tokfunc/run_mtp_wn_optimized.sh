#!/bin/bash
# Fleet-only: optimize the SAME already-guarded generated model, retaining the
# progressing reference binary/run. No new RTL elaboration or clock skipping.
set -euo pipefail
: "${REFERENCE:?completed one-WN build/run directory}"
OUT=${OUT:-wn_rank_optimized}
mkdir -p "$OUT/obj"
O=$(realpath "$OUT"); R=$(realpath "$REFERENCE")
python3 - "$R" "$O" <<'PY'
from pathlib import Path
import hashlib,json,os,sys
r,o=map(Path,sys.argv[1:]); obj=r/'build/obj'
assert (obj/'Vtb_mtp_wn_positions').is_file()
files=[]
for p in sorted(obj.iterdir()):
 if p.is_file() and p.suffix not in ('.o','.a','.d','.gch') and p.name!='Vtb_mtp_wn_positions':
  q=o/'obj'/p.name
  if not q.exists():os.link(p,q)
  files.append(dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
for name in ('stim.hex','mu.hex','projection.json'):
 q=o/name
 if not q.exists():os.link(r/name,q)
p=dict(reference=str(r),generated_source=files,rtl_source_manifest=(r/'build/sources.sha256').read_text(),
       compiler_flags=dict(OPT_FAST='-O3',OPT_SLOW='-O0',OPT_GLOBAL='-O2'),
       semantics='same guarded generated C++; no fast-math, source/clock/lane/date/payload changes')
(o/'source_identity.json').write_text(json.dumps(p,indent=2)+'\n')
PY
if [ ! -x "$O/obj/Vtb_mtp_wn_positions" ]; then
  /usr/bin/time -v -o "$O/time_build.log" make -C "$O/obj" -f Vtb_mtp_wn_positions.mk -j${JOBS:-8} \
    OPT_FAST=-O3 OPT_SLOW=-O0 OPT_GLOBAL=-O2 > "$O/build.log" 2>&1
fi
read -r NS NM < <(python3 - "$O/projection.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print(r['beats'],r['commands'])
PY
)
(cd "$O" && /usr/bin/time -v -o time_run.log obj/Vtb_mtp_wn_positions +NS="$NS" +NM="$NM" > run.log 2>&1)
grep -E '^WN_CFG|^WN_STATS|^PASS|^FAIL|^MISMATCH|^TAGBAD' "$O/run.log"
grep -q '^PASS mtp_wn_positions' "$O/run.log"
