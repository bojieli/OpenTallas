#!/bin/bash
# $1 = run dir, $2 = out file ; dumps sinks from 3_place.odb (pre-CTS: sinks on the original clock net)
ODB=$(find $1/run/results -name 3_place.odb | head -1)
[ -z "$ODB" ] && { echo "no odb $1"; exit 1; }
D=$(dirname $ODB); O=$(dirname $2); mkdir -p $O
docker run --rm --memory=24g --name hcl3dump_$(basename $1 | tail -c 20) -v $D:/d:ro -v $O:/o -v /tmp/hcl3:/s:ro openroad/orfs:asap7lock bash -lc "ODB=/d/3_place.odb OUT=/o/$(basename $2) /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/dump_sinks.tcl" > $2.log 2>&1
echo "$1 -> $(grep -c ^SINK $2) sinks"
