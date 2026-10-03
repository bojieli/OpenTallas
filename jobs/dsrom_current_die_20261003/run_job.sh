#!/bin/bash
set -eu
job=$1
out=$2
case "$job" in grt) peak=40; threads=16;; pin) peak=8; threads=1;; pdn) peak=64; threads=8;; *) exit 2;; esac
source "$HOME/.opentallas-env"
source_dir=$(pwd)
if [ -n "$(git status --porcelain -uno)" ]; then echo 'dirty tracked source refused' >&2; exit 1; fi
mkdir -p "$(dirname "$out")"
python3 tools/dsrom_current_die_feasibility.py --job "$job" --frame D --shard 0 --out "$out" > "$out.prepare.log" 2>&1
python3 - "$out" "$job" "$peak" "$threads" <<'PY'
import json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);(p/'launch.json').write_text(json.dumps({'source':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'job':sys.argv[2],'peak_GB_for_admission':int(sys.argv[3]),'threads':int(sys.argv[4]),'reserve_GB':150,'running_memory_time_caps':False,'source_tree_dirty':False},indent=2)+'\n')
PY
set +e
if [ "$job" = pin ]; then
 for kind in q bf cfg; do
  /srv/opentallas-scratch/admit.sh "$peak" -- docker run --rm -u 1000:1000 -v "$out:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads "$threads" -exit "/work/$kind.tcl" > "$out/$kind.log" 2>&1
  code=$?; echo "exit=$code" > "$out/$kind.exit_code"
  [ "$code" = 0 ] || break
 done
else
 /srv/opentallas-scratch/admit.sh "$peak" -- docker run --rm -u 1000:1000 -v "$out:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads "$threads" -exit /work/run.tcl > "$out/actual.log" 2>&1
 code=$?
fi
echo "exit=$code" > "$out/exit_code"
date -u +%FT%TZ >> "$out/exit_code"
exit "$code"
