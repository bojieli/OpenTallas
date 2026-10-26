#!/bin/bash
# Two necessary nominal calibration probes, on independently identified fresh
# STG3 binaries. Never builds, alters original objects, or runs a layer sweep.
set -euo pipefail
R=$(readlink -f "$1")
mkdir "$R/run"
for c in rel pos; do
  python3 - "$R" "$c" <<'PY' > "$R/run/$c.source_check.json"
from pathlib import Path
import hashlib, json, shlex, sys
r=Path(sys.argv[1]); c=sys.argv[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
s=json.loads((r/'SOURCE.json').read_text())
assert sha(r/'provenance/original/original_source_verification.json')==s['original_verification_sha256']
p=json.loads((r/'provenance/original/original_source_verification.json').read_text())['configs'][c]
for name,row in p['source_records'].items():
 assert row['committed_source_matches'] and all(row[k] for k in ('hash_matches','size_matches','inode_matches','mtime_matches','ctime_matches'))
 assert sha(r/'tree'/name)==row['sha256'], name
assert p['main_cpp_matches_c0'] and p['main_cpp_unchanged_before_compile'] and p['source_cpp_recorded_in_original_command']
assert sha(r/'tree/rtl/test/qwen_dv/main2.cpp')==p['main_cpp_sha256']
assert sha(r/'bin'/c/'Vtb')==p['binary_sha256']
assert sha(r/'tree/rtl/test/qwen_dv/dv_lower_mat_bench.py')==s['candidate_bench_sha256']
assert sha(r/'tree/tools/qwen_layerbench/dv_lower_mat.py')==s['lowering_helper_sha256']
assert sha(r/'run_stg_cal_prearm.sh')==s['runner_sha256']
assert sha(r/'original_records'/c/'build/obj_n12/Vtb__verFiles.dat')==p['original_dat_sha256']
assert sha(r/'original_records'/c/'build/build.log')==p['original_buildlog_sha256']
flags=['-GMUT=0','-GN=12','-GMU_NU=4','-GSU_LT=1']+(['-GARF=1','-GRP=1'] if c=='pos' else [])
assert [x for x in shlex.split(p['original_command']) if x.startswith('-G')]==flags
print(json.dumps(dict(verdict='PASS',scope='original compiler source records and exact copied binary; no prospective manifest backfill',configuration=c,binary_sha256=p['binary_sha256'],rtl_inputs=len(p['source_records']))))
PY
done
for c in rel pos; do
  W=$R/run/$c
  mkdir -p "$W/obj_n12"
  ln -s "$R/bin/$c/Vtb" "$W/obj_n12/Vtb"
  export DV_LOWER_VFLAGS='-GMU_NU=4 -GSU_LT=1'
  [ "$c" != pos ] || export DV_LOWER_VFLAGS="$DV_LOWER_VFLAGS -GARF=1 -GRP=1"
  set +e
  python3 - "$R" "$c" <<'PY' > "$W/calibrate.out" 2>&1
from pathlib import Path
import hashlib, importlib.util, json, sys
r=Path(sys.argv[1]); c=sys.argv[2]; work=r/'run'/c
spec=importlib.util.spec_from_file_location('calibration_candidate',r/'tree/rtl/test/qwen_dv/dv_lower_mat_bench.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=json.loads((r/'provenance/original/original_source_verification.json').read_text())['configs'][c]
def existing_only(_work):
 exe=_work/'obj_n12/Vtb'
 if not exe.is_file() or hashlib.sha256(exe.read_bytes()).hexdigest()!=p['binary_sha256']:
  raise SystemExit('REFUSED: exact verified executable missing/mismatched; building is prohibited')
 return exe
# Disable the cached builder entry point rather than relying on its existence
# check: a missing executable must never trigger an accidental hardware build.
b.LB.build=existing_only
raise SystemExit(b.calibrate(work,1))
PY
  rc=$?
  set -e
  echo "rc=$rc" >> "$W/calibrate.out"
done
python3 - "$R" <<'PY'
from pathlib import Path
import json,sys
r=Path(sys.argv[1]); rows={}
for c in ('rel','pos'):
 w=r/'run'/c;t=(w/'calibrate.out').read_text();p=w/'stn_ages.json';a=json.loads(p.read_text()) if p.exists() else {}
 ok=t.rstrip().endswith('rc=0') and 'CALIBRATE OK' in t and a.get('faults')==[] and all(a.get(k) is not None for k in ('l8_ar','ar_hop','xc_cc','amax_ami','arx_after_amv'))
 rows[c]=dict(verdict='PASS' if ok else 'FAIL',ages=a)
x=dict(verdict='PASS' if all(v['verdict']=='PASS' for v in rows.values()) else 'FAIL',scope='two nominal calibration-only probes on identified c0+a83 monolith; no new build, layer sweep, upstream MAC, selected-S8 or token-rate qualification',source=json.loads((r/'SOURCE.json').read_text()),cases=rows)
(r/'result.json').write_text(json.dumps(x,indent=1)+'\n')
print(json.dumps(x))
raise SystemExit(0 if x['verdict']=='PASS' else 1)
PY
