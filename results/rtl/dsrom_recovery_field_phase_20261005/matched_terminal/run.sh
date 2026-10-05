#!/bin/bash
set -eu
r=/srv/opentallas-scratch/codex/epicurus-field-phase-matched-20261005-r1
cd "$r"
trap 'rc=$?; printf "%s\n" "$rc" > terminal.exit' EXIT
v=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 - <<'PY'
import pathlib,json,hashlib,subprocess,datetime
r=pathlib.Path('.')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((r/'archive/build.json').read_text())
for n,h in b['source_sha256'].items():
 if sha(r/'retained-source'/n)!=h:raise ValueError('retained engine source changed: '+n)
files={str(p):sha(p) for d in ['src','archive','planv','retained-source','retained-runs'] for p in (r/d).rglob('*') if p.is_file()}
a=dict(source_commit='1002323510d8d64bbf90c97d0de7911d724218a5',timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),files_sha256=files,compiler=subprocess.check_output(['g++','--version'],text=True),meminfo=pathlib.Path('/proc/meminfo').read_text(),disk=subprocess.check_output(['df','-B1','.'],text=True),load=pathlib.Path('/proc/loadavg').read_text(),scope='matched scheduling only; reused archive; physical screen not closure',caps='no elapsed-time, FSIZE or guessed AS caps; shared measured-headroom admission16GiB plus100GiB reserve;8 simulation workers/1 link')
(r/'launch_inputs.json').write_text(json.dumps(a,indent=1)+'\n')
PY
/usr/bin/time -v -o link.metrics g++ -std=c++20 -O2 -fno-fast-math -ffp-contract=off -fno-associative-math -DNR=1 -DVAW=17 -I"$v/include" -I"$v/include/vltstd" -Iarchive src/rtl/test/dsrom_sys/tb_dsrom_field_phase_matched.cpp archive/Vpq__ALL.a "$v/include/verilated.cpp" "$v/include/verilated_threads.cpp" -pthread -o matched_tb > link.log 2>&1
/usr/bin/time -v -o run.metrics python3 src/tools/dsrom_field_phase_matched.py --plan-dir "$r/planv" --output "$r/runs" --tb "$r/matched_tb" --retained-runs "$r/retained-runs" --jobs 8 > run.log 2>&1
