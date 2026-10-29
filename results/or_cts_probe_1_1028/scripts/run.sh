#!/bin/bash
# usage: run.sh CASE VARIANT "OPTS"
B=/srv/opentallas-scratch2/claude/or-cts-probe-1; CASE=$1; V=$2; OPTS=$3
mkdir -p $B/$CASE/$V
for C in TT FF; do
docker run --rm --name orcts-$CASE-$V-$C --memory=48g --memory-swap=48g --cpus=4 -e CORNER=$C -e D=/w/$CASE -e V=$V -e OPTS="$OPTS" -e TRACKS=/w/tracks.tcl -v $B:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 4 -exit /w/cts.tcl > /w/$CASE/$V/log_$C.txt 2>&1; echo EXIT \$? >> /w/$CASE/$V/log_$C.txt; chown -R $(id -u):$(id -g) /w/$CASE/$V"
done
