#!/bin/bash
# run.sh TCL WI IT MEMG [LEFDIR]  -> hehot/o/WI.log   (DS85-HEHOT, DO_NOT_COUNT)
H=/srv/opentallas-scratch3/claude/die-s81-85; T=$1; WI=$2; IT=$3; M=$4; L=${5:-$H/hcabs/grt/h9/lef}
AV=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); [ $AV -ge $((M+32)) ] || { echo "no headroom $AV"; exit 3; }
mkdir -p $H/hehot/o
exec docker run --rm --name ds85-hehot-$WI --memory ${M}g --user $(id -u):$(id -g) -e WI=$WI -e IT=$IT -e MOVES="$MOVES" \
  -v $H/m6wi/h9:/r:ro -v $L:/l:ro -v $H/hehot/o:/o -v $H/hehot:/w:ro \
  --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad openroad/orfs:asap7lock -no_init -exit -threads 8 /w/$T > $H/hehot/o/$WI.log 2>&1
