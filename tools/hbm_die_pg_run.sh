#!/bin/bash
set -eu
D=${D:-/srv/opentallas-scratch/claude/hbmdie-v10}
B=$D/pg_1013
run() {
 n=$1; shift
 W=$B/$n
 ot-heavy --mem 4 -- python3 "$D/hbm_die_pg_assembly.py" "$@" --out "$W" > "$B/${n}_gen.log" 2>&1
 ot-heavy --mem 32 -- docker run --rm --name hbm_realpg_$n --cpus=8 --memory=32g -v "$W:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=$?; echo $rc > /work/run.exit; chmod -R a+rwX /work; exit $rc' || { echo "$(date -Is) $n FAILED" >> "$B/STATUS.log"; return 1; }
 echo "$(date -Is) $n DONE" >> "$B/STATUS.log"
}
run vm vm --root "$B/source_vm"
run sm sm --density 1.20 --sm-lef "$D/src_120f11b14_stn/physical/hbm_accel_die_views/sm/hfd_sm.lef"
echo "$(date -Is) ALL DONE" >> "$B/STATUS.log"
