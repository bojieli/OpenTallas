#!/bin/bash
# ROOT-authorized private exact-checkpoint vehicle; no synthesis, GPL or DRT.
set -euo pipefail
K=$1
GOAL=${2:-grt}
MEM=${3:-48}
THREADS=${4:-8}
case "$GOAL" in grt|verify) ;; *) echo "NOT RUN: accepts grt or read-only verify only"; exit 78;; esac
python3 - "$K" "$0" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
k=Path(sys.argv[1]); r=json.loads((k/'compiled_scope_contract.json').read_text())
assert r['goal']=='grt' and r['native_points']==13119
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(Path(sys.argv[2]))==r['runner_sha256'],'scope runner differs'
for n,v in r['hashes'].items():
    assert (k/n).is_file() and h(k/n)==v,('compiled input changed',n)
lec=json.loads((k/'qualified_native/lec.json').read_text())
assert lec['verdict']=='EQUIVALENT' and lec['counts']['proved']==13119
assert lec['reset_contract']['used']==4 and not lec['reset_contract']['debug_overrides']
for n in ['face_guard.json','face_guard_raw.json','reg_fanout.json']:
    assert json.loads((k/'qualified_native'/n).read_text())['verdict']=='PASS',n
base=next((k/'run/results/asap7').glob('*/base'))
assert not list(base.glob('4_*')) and not list(base.glob('5_*')) and not list(base.glob('6_*')),'not a fresh G1 successor'
image=subprocess.check_output(['docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip()
assert image==r['platform_image_id'],'platform library/image context changed'
print('COMPILED_G2_SCOPE_BIND PASS: exact qualified13119RTL/nativeproof, G1checkpoint, libraries/image, fixed807tree and all101inputs; no newproof claim')
PY
if [ "$GOAL" = verify ]; then exit 0; fi
docker run --rm --name "codex-rt-compiled-grt-$$" --cpus "$THREADS" --memory "${MEM}g" --memory-swap "${MEM}g" \
  -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/kit_modes.py check /work --step cts
grep -q "^override export OT_HOLD_MM = 1" /work/config.mk
grep -q "^override export OT_MM_SETUP_CORNER = tc" /work/config.mk
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
M="make --no-print-directory -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES='"$THREADS"'"
$M do-cts
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair
HM=$(sed -n "s/^export OT_HOLD_FF_MARGIN = //p" /work/config.mk)
test -n "$HM"
$M do-grt HOLD_SLACK_MARGIN="$HM"
if ! python3 -I /work/legacy_gate.py /work grt; then
  echo "FAIL_POSTCTS exact compiled scope: canonical TT/standardFF/CPPR G2 guard failed" >> /work/FAIL_POSTCTS
  exit 2
fi
test -z "$(find /work/run/results -name 5_2_route.odb -o -name 5_route.odb -o -name 6_final.odb)"
echo "COMPILED_G2_SCOPE_DONE: normal fixed-tree CTS + canonical MM GRT + actual policy G2; NO DRT"
'
