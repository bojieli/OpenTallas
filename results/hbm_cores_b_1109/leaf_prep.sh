#!/bin/bash
# S81-TYPES-10 leaf batch prep: per item on its own kit host. args: lines "item|attempt_dir"
W=/srv/opentallas-scratch2/claude/s81-types-10/leafbatch; mkdir -p $W/in
P=/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/plan_h2_2249.json
while IFS='|' read -r it A; do
  K=$A/gen/$it; R=$K/run/results/asap7/dp_$it/base; O=$W/in/$it; mkdir -p $O
  cp $K/macro_place.tcl $K/io.tcl $O/ 2>/dev/null
  [ -f $K/macro_moves.json ] && cp $K/macro_moves.json $O/
  ODB=$(ls $R/3_place.odb $R/2_floorplan.odb $R/1_synth.odb 2>/dev/null | head -1)
  echo "$it $ODB" >> $W/in/_odb.txt
  [ -s $O/conn.json ] || docker run --rm --name s81t10-conn-$$-${it//[^a-zA-Z0-9]/} --cpus=2 --memory=24g -v $W:/w -v "$R":/odb:ro -w /w openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit -no_splash /w/conn.py /odb/$(basename $ODB) /w/in/$it/conn.json" > $O/conn.log 2>&1
  echo "$it conn rc=$? $(tail -1 $O/conn.log | cut -c1-120)" >> $W/in/_done.txt
done
