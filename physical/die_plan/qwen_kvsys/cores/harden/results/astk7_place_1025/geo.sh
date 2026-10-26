#!/bin/bash
# usage: geo.sh <results base dir> <outdir> <title>   (diagnostic, docker --memory 8g)
R=$1; OUT=$2; T=$3; S=/srv/opentallas-scratch2/claude/path-kv-astk7
mkdir -p $OUT
docker run --rm --memory=8g -u $(id -u):$(id -g) -v $R:/r:ro -v $OUT:/o -v $S:/s:ro -e ODB=/r/3_place.odb -e OUT=/o -e FACEF=/r/ot_face_flops.txt openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /s/geo_dump.tcl > /o/dump.log 2>&1"; tail -1 $OUT/dump.log
python3 $S/geo_check.py $OUT "$T"
