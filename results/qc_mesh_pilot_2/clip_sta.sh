#!/bin/bash
# QC-MESH-PILOT-2: re-time every routed clip (drt.odb + drt.spef) at TT and FF with the composed entry slew, then
# compose the full-region routed tree files.  usage: clip_sta.sh CLIPROOT TRIAL_DIR   (run where the clips ran)
set -e
R=$(cd $1 && pwd); T=$(cd $2 && pwd); S=$(cd $(dirname $0) && pwd)
sta() {  # clip corner slew mid
  docker run --rm --name qcmp2-sta-$(basename $R)-$1-$2-$$ --memory=8g --cpus=2 -e CORNER=$2 -e SLEW=$3 -e MID=$4 -e TAG= \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $R/$1:/o openroad/orfs:asap7lock bash -lc \
    'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/sta.tcl > /o/sta_$CORNER.log 2>&1; chown -R 1000:1000 /o' &
}
for C in TT FF; do sta mid $C 0 1; done; wait
for C in TT FF; do
  for c in c0 c1 c2 c3 core; do
    e=$(python3 -c "import json;print(json.load(open('$R/$c/clip.json'))['entry'])")
    sl=$(awk -v e=$e '$1=="A" && $2==e {print $5}' $R/mid/tree_drt_$C.txt)
    echo "$C $c entry $e slew $sl"
    sta $c $C $sl 0
  done
done
wait
for C in TT FF; do python3 $S/pilot_clip.py compose $T $R drt $C $R/tree_drt_$C.txt; done
python3 $S/pilot_clip.py compose $T $R grt TT $R/tree_grtclip_TT.txt
