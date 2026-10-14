#!/bin/bash
set -euo pipefail
K=$1
M=$PWD
export SRC=$M/src VEC=$M/vec OUT=$M/out
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p out
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $K $*" >> "$M/run.log"; }
log "start pid=$$ source $(cat src/COMMIT)"
bash "build_$K.sh"
log 'build rc=0'
LAYERS='24 20 2'
[ "$K" != BASE ] && LAYERS=20
for L in $LAYERS; do
    mkdir -p "out/$K/ds_L$L"
    (
        cd "out/$K/ds_L$L"
        "$M/out/$K/obj/tb" +DIR="$M/vec/ds_L$L" +OUT="$M/out/$K/ds_L$L/e2e_records.txt" > run.log 2>&1
        log "L$L simulation rc=0 (verdict in run.log)"
    ) &
done
wait
log DONE
