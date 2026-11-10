#!/bin/bash
# FACEHOLD-S81 census on a read-only copy of a row's routed DB (epyc8 facehold/<ROW>): the row's own signoff FF session
# cut before "so_timing STD" + census_tail.tcl.  Capped container (docker --memory), admission: MemAvailable >= cap+32G.
# usage: census_run.sh ROW [CORNER=ff]
set -eu
R=$1; C=${2:-ff}; CAP=${CAP:-64}
F=/srv/opentallas-scratch2/claude/die-s81-85/facehold
D=$F/$R; O=$D/census_$C; mkdir -p $O
avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
[ "$avail" -ge $((CAP + 32)) ] || { echo "admission: MemAvailable ${avail}G < cap ${CAP}G + 32G"; exit 3; }
S=${C%2}; n=$(grep -n "^so_timing STD" $D/$S/session.tcl | head -1 | cut -d: -f1)
[ -n "$n" ] || { echo "no so_timing STD line"; exit 4; }
head -n $((n - 1)) $D/$S/session.tcl > $O/probe.tcl
if [ $C = tt2 ]; then cat $F/census_tail_tt2.tcl; elif [ $C = tt ]; then cat $F/census_tail_tt.tcl; else cat $F/census_tail.tcl; fi >> $O/probe.tcl
cp $D/$S/libraries.json $O/libraries.json
docker run --rm --name fh_census_${R}_${C}_$$ --cpus=8 --memory=${CAP}g --memory-swap=${CAP}g \
  -v $D/base:/base:ro -v $D/$S/sdcdir:/sdc:ro -v $O:/out -v $D/config.mk:/work/config.mk:ro openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/probe.tcl > $O/probe.log 2>&1
echo "rc=$?" > $O/rc
docker run --rm -v $O:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out >/dev/null 2>&1 || true
cat $O/rc
