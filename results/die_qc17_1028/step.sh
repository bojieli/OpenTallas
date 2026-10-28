#!/bin/bash
# DIE-QC-17: step.sh <nl|nk> plan <tag> [plan opts] | step.sh <nl|nk> <prev> <new>  (shared parent_trunk_dme, my wt)
# plan/corr on ROUTED clock-GRT TT arrivals -> tcl -> parent_trunk_insert.tcl -> clock GRT TT/FF -> ocv (OCV-inclusive spread)
set -u; D=$1; p=$2; g=$3; shift 3; R=/srv/opentallas-scratch2/claude/die-qc17-1028; N=$R/$D
T=/srv/opentallas-scratch2/claude/wt/die-qc17-1028/tools/die_plan; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/$D
if [ $D = nl ]; then ODBD=/srv/opentallas-scratch2/claude/die-qc15-1028/nl; ODB=cl_nlr.odb; G=cl_nl.json; CI=clins_nl.json; OR=""
elif [ $D = nl2 ]; then ODBD=$N; ODB=cl_nlr.odb; G=cl_nl.json; CI=clins_nl.json; OR=""; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/nl
else ODBD=/srv/opentallas-scratch2/claude/die-qc14-1028/a0trunk; ODB=cl_nkr.odb; G=cl_nk.json; CI=clins_nk2.json; OR="--orient-rule 200"; fi
cd $N
if [ "$p" = plan ]; then
  python3 -I $T/parent_trunk_dme.py plan $G $CI trunk_$g.json --entry 228.972,578.88 --pin-offset ot_qwen_tile_romleaf=21.612,15.12 $OR "$@" > plan_$g.log 2> plan_$g.err || exit 1
else
  python3 -I $T/parent_trunk_dme.py corr trunk_$p.json arr_r${p}_TT.txt trunk_$g.json "$@" > corr_$g.log || exit 1
fi
python3 -I $T/parent_trunk_dme.py tcl trunk_$g.json trunk_$g.tcl || exit 1
docker run --rm --name qc17-ins-$D-$g --cpus=4 --memory=12g -v $P:/p:ro -v $N:/w -v $ODBD:/o:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/o/$ODB TTCL=/w/trunk_$g.tcl OUT=/w/tr_$g.odb openroad -exit /w/ins_wrap.tcl" > ins_$g.log 2>&1 || { echo ins fail; exit 1; }
for C in TT FF; do docker run --rm --name qc17-grt-$D-$g-$C --cpus=4 --memory=16g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=$C ODB=/w/tr_$g.odb OUT=/w/arr_r${g}_$C.txt openroad -threads 4 -exit /w/grt.tcl; echo EXIT \$?" > grt_${g}_$C.log 2>&1 & done; wait
grep -h EXIT grt_${g}_TT.log grt_${g}_FF.log | tr "\n" " "
python3 -I $T/parent_trunk_dme.py ocv trunk_$g.json arr_r${g}_TT.txt arr_r${g}_FF.txt ocv_$g.json > /dev/null && python3 -c "import json;o=json.load(open(\"ocv_$g.json\"));print(\"$D $g\", {C:(o[C][\"nominal_spread\"],o[C][\"ocv_inclusive_spread\"]) for C in o})"
echo "step $D $g done $(date)"
