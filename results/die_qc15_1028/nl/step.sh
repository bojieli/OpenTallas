#!/bin/bash
# DIE-QC-15 nl: step.sh plan q0 | step.sh <prev> <new>  (shared parent_trunk_dme; corr on ROUTED clock-GRT TT arrivals)
# -> tcl -> shared parent_trunk_insert.tcl on cl_nlr.odb (a0k5 romleaf pin) -> clock GRT TT/FF -> eval
set -u; p=$1; g=$2; N=/srv/opentallas-scratch2/claude/die-qc15-1028/nl; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nl
TOOLS=/srv/opentallas-scratch2/claude/wt/die-qc15-1028/tools/die_plan; cd $N
if [ "$p" = plan ]; then
  python3 -I $TOOLS/parent_trunk_dme.py plan cl_nl.json clins_nl.json trunk_$g.json --entry 228.972,578.88 --pin-offset ot_qwen_tile_romleaf=21.612,15.12 > corr_$g.log || exit 1
else
  python3 -I $TOOLS/parent_trunk_dme.py corr trunk_$p.json arr_r${p}_TT.txt trunk_$g.json ${EXTRA:-} > corr_$g.log || exit 1
fi
python3 -I $TOOLS/parent_trunk_dme.py tcl trunk_$g.json trunk_$g.tcl || exit 1
cp $TOOLS/parent_trunk_insert.tcl $N/; echo "source /w/common.tcl; source /w/parent_trunk_insert.tcl" > ins_wrap.tcl
docker run --rm --name qc15-nlins-$g --cpus=4 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/w/cl_nlr.odb TTCL=/w/trunk_$g.tcl OUT=/w/tr_$g.odb openroad -exit /w/ins_wrap.tcl" > ins_$g.log 2>&1 || { echo ins fail; exit 1; }
for C in TT FF; do docker run --rm --name qc15-nlgrt-$g-$C --cpus=4 --memory=16g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/tr_$g.odb OUT=/w/arr_r${g}_$C.txt openroad -threads 4 -exit /w/grt.tcl; echo EXIT \$?" > grt_${g}_$C.log 2>&1 & done; wait
sed "s/arr_rq4_/arr_r${g}_/g; s/trunk_q4.json/trunk_$g.json/; s/evr_q4.json/evr_$g.json/; /placement_rc_q4/d; /pl = json.load/d" evr.py > evr_$g.py; python3 -I evr_$g.py > evr_$g.log; echo "step $g done $(date)"
