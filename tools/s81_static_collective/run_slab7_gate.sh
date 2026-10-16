#!/usr/bin/env bash
# Existing actual128SRAM slab bench with explicit delivered CAL7 clocks.
# Arguments: WORK [CLOCK_MUT [DATA_MUT]]. Clock mutant1 stops ROM0,2 stops output0.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
W=$(mkdir -p "$1" && cd "$1" && pwd)
CLOCK_MUT=${2:-0}
DATA_MUT=${3:-0}
python3 "$ROOT/tools/s81_static_collective/build_slab7.py" --out "$W/generated"
python3 - "$ROOT" "$W" "$CLOCK_MUT" "$DATA_MUT" <<'PY'
from pathlib import Path
import sys
root,work=map(Path,sys.argv[1:3]);clock_mut,data_mut=map(int,sys.argv[3:5])
s=(root/'tools/s81_static_collective/run_slab_gate.sh').read_text()
def one(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)
one('ROOT=$(cd "$(dirname "$0")/../.." && pwd);', 'ROOT='+str(root)+';')
one('"$ROOT/tools/s81_static_collective/tb_s81_static_collective_slab.sv"',
    '"$W/generated/dsfd_sp_collective_static_c7.sv" "$W/generated/s81_static_collective_slab7.sv" "$W/generated/tb_s81_static_collective_slab.sv"')
one('-GMUT="$MUT"', '-GCALENDAR_CLOCK_MUT='+str(clock_mut)+' -GMUT="$MUT"')
one('--out "$W" > fixture.json', '--out "$W" --vm-read-edges 18 > fixture.json')
if clock_mut:
    one('MUT=${2:-0};', 'MUT=${2:-0}; MUTANT=1;')
(work/'runner.sh').write_text(s)
PY
bash "$W/runner.sh" "$W" "$DATA_MUT" 1 1
