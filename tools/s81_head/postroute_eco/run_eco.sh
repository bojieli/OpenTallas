#!/bin/bash
set -uo pipefail
K=$(cd "$1" && pwd)
docker run --rm --name codex-head-rcx-$$ --memory=48g --memory-swap=48g --cpus=16 -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /work/run_inside.sh > "$K/run_extracted.log" 2>&1
rc=$?
docker run --rm -v "$K:/work" openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
if [ "$rc" = 0 ]; then
 python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image openroad/orfs:asap7lock > "$K/signoff.log" 2>&1
 rc=$?
 grep -E '^SIGNOFF|^  - ' "$K/signoff.log"
fi
printf 'exit=%s\n' "$rc" > "$K/rc.txt"
exit "$rc"
