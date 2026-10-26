#!/bin/bash
# ONE CTS-only no-ID TKM clock prototype (trial): resume the kit's own validated 1_synth checkpoint, make cts only.
# No GRT/DRT/signoff. Same runner body as Codex run_tkm_clock_cts1713.sh (codex/hbm-clock-1713), plus a
# rule-3 guard: the kit must name its source_commit and repo-relative plan/pins/rtl paths.
#   run_tkm_clock_cts.sh KIT [cts] [MEM_GB=32] [THREADS=8]      (heavy: via ot-run / autopilot)
set -euo pipefail
kit=$(cd "$1" && pwd -P)
requested=${2:-cts}
mem=${3:-32}
threads=${4:-8}
python3 - "$kit" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.load(open(p/'source_receipts/qualification.json'))
f=json.load(open(p/'freeze.json'))
if not f.get('source_commit') or any(str(x).startswith('/') for x in [f.get('plan'),f.get('pins_file')]+[v['path'] for v in f.get('rtl_overrides',{}).values()]):raise SystemExit('NOT RUN: kit is not rule-3 (source_commit + repo-relative plan/pins/rtl)')
if r.get('minimum_miter')!='PASS' or r.get('mutant')!='CAUGHT':raise SystemExit('NOT RUN: no-ID minimum gate unavailable')
if json.load(open(p/'source_receipts/lec.json')).get('verdict')!='EQUIVALENT':raise SystemExit('NOT RUN: actual synthesis LEC not EQUIVALENT')
actual=hashlib.sha256((p/r['canonical_file']).read_bytes()).hexdigest()
for name,expected in r['rtl_sha256'].items():
 if hashlib.sha256((p/name).read_bytes()).hexdigest()!=expected:raise SystemExit('NOT RUN: synthesis-bound RTL changed: '+name)
if r.get('canonical_sha256')!=actual:raise SystemExit('NOT RUN: canonical source differs from proven source')
n=r.get('netlist_sha256',{})
for name,expected in n.items():
 if hashlib.sha256((p/name).read_bytes()).hexdigest()!=expected:raise SystemExit('NOT RUN: synth netlist differs from the LEC-proved one: '+name)
print('TKM_CLOCK_SOURCE_PASS',actual,'source_commit',f['source_commit'],'kit_hash',f['kit_hash'])
PY
mapfile -t odbs < <(find "$kit/run/results" -name 1_synth.odb -type f)
[ "${#odbs[@]}" = 1 ] && [ -s "${odbs[0]}" ] || { echo 'NOT RUN: missing unique validated synth checkpoint'; exit 3; }
checkpoint=/work/${odbs[0]#"$kit/"}
if [ -f "$kit/placement_resume.json" ]; then
 checkpoint=$(python3 - "$kit" <<'PYCHECK'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.load(open(p/'placement_resume.json'));f=json.load(open(p/'freeze.json'))
if r.get('scope')!='identical_rtl_pins_placement_clock_port_fix':raise SystemExit('NOT RUN: wrong placement-resume scope')
if r.get('pins_sha256')!=f['pins_sha256']:raise SystemExit('NOT RUN: resumed placement pin contract changed')
if hashlib.sha256((p/'io.tcl').read_bytes()).hexdigest()!=r['io_sha256']:raise SystemExit('NOT RUN: resumed placement io changed')
for name,h in r['files'].items():
 q=Path(name)
 if q.is_absolute() or '..' in q.parts or not name.startswith('run/'):raise SystemExit('NOT RUN: invalid checkpoint path')
 if hashlib.sha256((p/q).read_bytes()).hexdigest()!=h:raise SystemExit('NOT RUN: checkpoint changed: '+name)
q=r['checkpoint']
if not q.endswith('/3_place.odb') or q not in r['files']:raise SystemExit('NOT RUN: no verified 3_place checkpoint')
if not any(x.endswith('/3_place.sdc') for x in r['files']):raise SystemExit('NOT RUN: missing placement SDC')
print('/work/'+q)
PYCHECK
 )
fi
printf '%s\n' 'ONE CTS-only noID clock prototype; no GRT/DRT/signoff. Review actual tree before TT/FF probes.' > "$kit/DIAGNOSTIC_ONLY"
printf 'requested=%s enforced=cts checkpoint=%s\n' "$requested" "$checkpoint"
docker_cmd=(docker)
if ! docker ps >/dev/null 2>&1; then docker_cmd=(sudo docker);fi
"${docker_cmd[@]}" run --rm --cpus="$threads" --memory="${mem}g" --memory-swap="${mem}g" \
 -v "$kit":/work -e HUID="$(id -u)" -e HGID="$(id -g)" \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$1" -o "$2" cts; chown -R "$HUID:$HGID" /work/run' tkm-clock "$threads" "$checkpoint"
