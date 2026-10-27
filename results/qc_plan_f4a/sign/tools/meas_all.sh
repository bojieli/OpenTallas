#!/bin/bash
# QC-SU-F4A-SIGN: meas_ck.tcl (QC-SU-KITS-3) per-sink clock arrivals: GRT (prehold 5_1_grt, rc_cal) and RCX (6_final SPEF)
# usage: meas_all.sh KIT TAG ODB_RCX_DIR(rel kit)  -> KIT/meas/{grt,rcx}_{TT,FF}_TAG.tsv
D=$(cd "$(dirname "$0")" && pwd); k=$1; tag=$2; R=$3
B=$(cd $D/$k && ls -d run/results/asap7/*/base); mkdir -p $D/$k/meas
for C in TT FF; do
 docker run --rm --memory=12g --memory-swap=12g --cpus=2 -v $D/$k:/work:ro -v $D/$k/meas:/out -v $D/meas_ck.tcl:/m.tcl:ro -e ODB=/work/$R/6_final.odb -e SDC=/work/$R/6_final.sdc -e SPEF=/work/$R/6_final.spef -e OT_CORNER=$C -e OUT=/out/rcx_${C}_$tag.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl' > $D/$k/meas/rcx_${C}_$tag.log 2>&1 &
 if [ "$tag" = prehold ]; then
 docker run --rm --memory=12g --memory-swap=12g --cpus=2 -v $D/$k:/work:ro -v $D/$k/meas:/out -v $D/meas_ck.tcl:/m.tcl:ro -e ODB=/work/$B/5_1_grt_prehold.odb -e SDC=/work/$B/5_1_grt.sdc -e OT_CORNER=$C -e OUT=/out/grt_${C}.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl' > $D/$k/meas/grt_${C}.log 2>&1 &
 fi
done; wait
docker run --rm -v $D/$k/meas:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
grep -h MEAS_DONE $D/$k/meas/*.log
