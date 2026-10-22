#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
exec 9>.build_only.lock
flock -n 9 || { echo 'REFUSED: same minimum build already active'; exit 73; }
[ "$(sha256sum source.sha256 | cut -d' ' -f1)" = 64bb832617079f0759ca5a527f587d5caaf98c372a5571a40d66949fefb649ce ] || { echo 'REFUSED: manifest identity mismatch'; exit 72; }
sha256sum --check --quiet source.sha256
python3 - <<'GUARD'
from pathlib import Path
import json
root=Path.cwd().resolve()
if (root/'out').exists() and any((root/'out').iterdir()):
 raise SystemExit('REFUSED: existing output contents require explicit continuation review')
x=json.loads((root/'preflight.json').read_text())
assert x['NEV_required']==5968 and x['fixed_end']==85510 and x['fault_faces']==85
assert x['compile_global_defines']==[] and len(x['preprocessed_master_defines'])==48
assert sum(bool(v) for v in x['preprocessed_master_defines'].values())==4
live=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cwd=(p/'cwd').resolve();comm=(p/'comm').read_text().strip()
  if comm in ('verilator_bin','make','g++','c++','cc1plus','Vtb_hbm_slice') and (cwd==root or root in cwd.parents):live.append(p.name)
 except (OSError,RuntimeError):pass
if live:raise SystemExit('REFUSED: live samecase child '+str(live))
print('EXACT_CANDIDATE_GUARDS_PASS NEV5968 FIXED_END85510 FAULT85',flush=True)
GUARD
[ ! -e out/obj ] || { echo 'REFUSED: prior build objects require explicit same-source continuation review'; exit 74; }
VL="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
[ "$(sha256sum "${VL}_bin" | cut -d' ' -f1)" = d3f42fa3b523cf1d7e38827134ac8560ac03b52466392eaf0001141ed4d9fe41 ] || { echo 'REFUSED: Verilator binary identity mismatch'; exit 75; }
mkdir -p out
{ date -u '+START %Y-%m-%dT%H:%M:%SZ'; hostname; "$VL" --version; g++ --version | head -1; sha256sum source.sha256 build_only.sh; } > out/start_identity.txt
export SRC="$PWD/bundle" OUT="$PWD/out" JOBS=8 BUILD_ONLY=1
export REPLAY=slice/replay/replay_candidate
export CYCLES=85510
unset MAKEFLAGS MFLAGS
bash bundle/run_slice_vehicle.sh
[ -x out/obj/Vtb_hbm_slice ]
sha256sum out/obj/Vtb_hbm_slice > out/binary.sha256
# Build-only: no executable invocation/replay in this runner.
