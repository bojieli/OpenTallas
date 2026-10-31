#!/bin/bash
# usage: census.sh ODB SDC SETRC OUT   (docker, 16 GB cap)
D=$(cd $(dirname $1) && pwd); C=/srv/opentallas-scratch2/claude/die-kv-47-hr/census; S=$(cd $(dirname $3) && pwd); Q=$(cd $(dirname $2) && pwd)
docker run --rm --cpus 4 --memory 16g --memory-swap 16g -v $D:/db:ro -v $Q:/sdc:ro -v $S:/kit:ro -v $C:/c openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; LIBS_FILE=/c/libs_tt.txt ODB=/db/$(basename $1) SDC=/sdc/$(basename $2) SETRC=/kit/$(basename $3) OUT=/c/$4 openroad -exit /c/census.tcl" > $C/$4.log 2>&1
