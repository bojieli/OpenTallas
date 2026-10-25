#!/bin/bash
# PATH-QC-SRAMIF: GEOM-REVIEW F6 dump (reviewer's dumpif.py / dumpif_in.py, unchanged) on run results STAGE.odb + table.
K=$(cd "$1" && pwd); ST=${2:-3_place}; IMAGE=openroad/orfs:asap7lock
B=$(ls -d $K/run/results/asap7/*/base | head -1); BB=/work/run/results/asap7/$(basename $(dirname $B))/base
mkdir -p $K/f6_$ST
docker run --rm --name sramif-f6-$ST-$$ --memory=8g --memory-swap=8g -v $K:/work -v $K/f6_$ST:/out -w /work -e ODB=$BB/$ST.odb -e KIT=/work -e TAG=x $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/dumpif.py; openroad -python -exit /work/dumpif_in.py; chown -R $(id -u):$(id -g) /out"
python3 -I $K/f6_table.py $K/f6_$ST/macro_if.tsv $K/f6_$ST/x_in.tsv | tee $K/f6_$ST/F6_TABLE.tsv
