#!/bin/bash
cd "$(dirname "$0")"
T=$(python3 -c "import json;print(' '.join(json.load(open('index.json'))))")
for t in $T; do for v in old new; do echo "$t $v"; done; done | xargs -P 12 -n 2 ./run_one.sh
for t in $T; do echo $t; done | xargs -P 12 -n 1 ./equiv_one.sh
echo DONE
