#!/bin/bash
# DIE-QC-18: plan0.sh <nk> <tag> [plan opts]: plan -> insert on cl_nkr.odb -> full clock GRT (routes kept in g_<tag>.odb) -> TT/FF stored-route arrivals -> ocv
set -u; D=$1; g=$2; shift 2; R=/srv/opentallas-scratch2/claude/die-qc18-1028; N=$R/$D
T=/srv/opentallas-scratch2/claude/wt/die-qc18-1028/tools/die_plan; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/${PD:-$D}
cd $N
python3 -I $T/parent_trunk_dme.py plan cl_$D.json clins_$D.json trunk_$g.json --entry 228.972,578.88 --pin-offset ot_qwen_tile_romleaf=21.612,15.12 --orient-rule 200 "$@" > plan_$g.log 2> plan_$g.err || exit 1
cp trunk_$g.json trunk_${g}_built.json
python3 -I $T/parent_trunk_dme.py tcl trunk_$g.json trunk_$g.tcl || exit 1
docker run --rm --name qc18-ins-$D-$g --cpus=4 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; CORNER=TT ODB=/w/cl_${D}r.odb TTCL=/w/trunk_$g.tcl OUT=/w/tr_$g.odb openroad -exit /w/ins_wrap.tcl" > ins_$g.log 2>&1 || { echo ins fail; exit 1; }
docker run --rm --name qc18-full-$D-$g --cpus=4 --memory=16g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; MODE=full CORNER=TT ODB=/w/tr_$g.odb OUT=/w/arrfull_$g.txt ODB_OUT=/w/g_$g.odb openroad -threads 4 -exit /w/ptgrt.tcl; echo EXIT \$?" > full_$g.log 2>&1
for C in TT FF; do docker run --rm --name qc18-m-$D-$g-$C --cpus=2 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; MODE=inc CORNER=$C ODB=/w/g_$g.odb OUT=/w/arr_${g}_$C.txt openroad -threads 2 -exit /w/ptgrt.tcl; echo EXIT \$?" > m_${g}_$C.log 2>&1 & done; wait
python3 -I $T/parent_trunk_dme.py ocv trunk_${g}_built.json arr_${g}_TT.txt arr_${g}_FF.txt ocv_$g.json > /dev/null && python3 -c "import json;o=json.load(open(\"ocv_$g.json\"));print(\"$D $g\", {C:(o[C][\"nominal_spread\"],o[C][\"ocv_inclusive_spread\"]) for C in o})"
echo "plan0 $D $g done $(date)"
