#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 1 --memory 4g --memory-swap 4g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
yosys -V > tool_version.txt
for c in correct wrong_plain_data reset_support_OR control_forced_one; do
 r=0
 yosys -Q -T -s "$c.ys" > "$c.log" 2>&1 || r=$?
 printf "%s\n" "$r" > "$c.rc"
done
python3 check_lemma.py
' > lemma.log 2>&1 || r=$?
printf '%s\n' "$r" > lemma.rc
exit "$r"
