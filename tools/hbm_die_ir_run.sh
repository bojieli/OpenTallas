#!/bin/bash
set -eu
D=${D:-/srv/opentallas-scratch/claude/hbmdie-v10}
PY=$D/hbm_die_ir_window.py
B=$D/ir_1012
mkdir -p "$B"
run() {
 name=$1; cov=$2; shift 2
 W=$B/$name
 ot-heavy --mem 4 -- python3 "$PY" generate --model "$D/sta_stn/clock/model.json.gz" --lef "$D/sta_stn/case/elements.lef" --pg-lef "$D/sta_stn/case/views.lef" --window "$@" --coverage "$cov" --out "$W" > "$B/${name}_gen.log" 2>&1
 ot-heavy --mem 32 -- docker run --rm --name hbm_ir_1012_$name --cpus=8 --memory=32g -v "$W:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=$?; echo $rc > /work/run.exit; chmod -R a+rwX /work; exit $rc' || { echo "$(date -Is) $name solver failed" >> "$B/STATUS.log"; return 1; }
 python3 "$PY" record --out "$W" > "$B/${name}_record.log" 2>&1
 echo "$(date -Is) $name DONE" >> "$B/STATUS.log"
}
run vmSW .0878 13300 8900 14500 10800
run smSW .0878 700 2200 2400 3200
run svcSW .1639 1400 1150 2600 1750
echo "$(date -Is) ALL DONE" >> "$B/STATUS.log"
