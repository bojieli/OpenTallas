#!/bin/bash
# DIE-QC-15 routed re-balance step: step.sh <prev> <new>: shared parent_trunk_dme corr on ROUTED (clock GRT) TT arrivals
# of <prev> -> tcl -> shared parent_trunk_insert.tcl on cl_nkr.odb -> clock GRT TT/FF -> eval
set -u; p=$1; g=$2; A=/srv/opentallas-scratch2/claude/die-qc15-1028/rq4; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nk
TOOLS=/srv/opentallas-scratch2/claude/wt/die-qc15-1028/tools/die_plan; cd $A
python3 -I $TOOLS/parent_trunk_dme.py corr trunk_$p.json arr_r${p}_TT.txt trunk_$g.json > corr_$g.log || exit 1
python3 -I $TOOLS/parent_trunk_dme.py tcl trunk_$g.json trunk_$g.tcl || exit 1
cp $TOOLS/parent_trunk_insert.tcl $A/
echo "source /w/common.tcl; source /w/parent_trunk_insert.tcl" > ins_wrap.tcl
docker run --rm --name qc15-ins-$g --cpus=4 --memory=12g -v $P:/p:ro -v $A:/w -v /srv/opentallas-scratch2/claude/die-qc14-1028/a0trunk:/q14:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/q14/cl_nkr.odb TTCL=/w/trunk_$g.tcl OUT=/w/tr_$g.odb openroad -exit /w/ins_wrap.tcl" > ins_$g.log 2>&1 || { echo ins fail; exit 1; }
for C in TT FF; do docker run --rm --name qc15-grt-$g-$C --cpus=4 --memory=16g -v $P:/p:ro -v $A:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/tr_$g.odb OUT=/w/arr_r${g}_$C.txt openroad -threads 4 -exit /w/grt.tcl; echo EXIT \$?" > grt_${g}_$C.log 2>&1 & done; wait
sed "s/rq4/r$g/g; s/trunk_q4.json/trunk_$g.json/; s/evr_q4.json/evr_$g.json/" evr.py > evr_$g.py; python3 -I evr_$g.py > evr_$g.log; echo "step $g done $(date)"
