#!/bin/bash
# usage: probe.sh RUNDIR(src + results) OUT PD  -- on the fleet host; docker 24 GB cap
R=$1; O=$2; PD=$3; mkdir -p $O; cp $(dirname $0)/place.tcl $(dirname $0)/tv2.tcl $(dirname $0)/pin_reg_face_fence.tcl $O/
cp $(dirname $0)/hooks.tcl $O/hooks.tcl 2>/dev/null
ODB=$(ls $R/routes/gate/work/orfs/results/asap7/*/base/3_2_place_iop.odb)
ENVF=$(dirname $0)/env.list
docker run --rm --name tfprobe_$(basename $O)_$$ --memory=24g --memory-swap=24g --env-file $ENVF -e PD=$PD -v $O:/work -v $R/src:/src:ro -v $ODB:/in/in.odb:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/place.tcl > /work/place.log 2>&1; echo PLACE_RC \$?; sed -i 's#read_db .*#read_db /work/placed.odb#' /work/tv2.tcl; openroad -no_init -exit /work/tv2.tcl > /work/tv.log 2>&1; echo TV_RC \$?"
