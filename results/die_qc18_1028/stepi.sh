#!/bin/bash
# DIE-QC-18 incremental corr step: stepi.sh <nl|nk> <prev> <new> [corr opts]
#  corr on prev as-built + its stored-route TT arrivals -> eco (only changed legs) -> inc GRT (keeps other routes) ->
#  TT/FF re-measure of the stored routes -> ocv.  Shared tools from my wt (parent_trunk_dme.py eco, parent_trunk_grt.tcl)
set -u; D=$1; p=$2; g=$3; shift 3; R=/srv/opentallas-scratch2/claude/die-qc18-1028; N=$R/$D
T=/srv/opentallas-scratch2/claude/wt/die-qc18-1028/tools/die_plan; P=/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/${PD:-$D}
cd $N
python3 -I $T/parent_trunk_dme.py corr trunk_${p}_built.json arr_${p}_TT.txt trunk_$g.json "$@" > corr_$g.log || exit 1
python3 -I $T/parent_trunk_dme.py eco trunk_${p}_built.json trunk_$g.json eco_$g.tcl trunk_${g}_built.json > eco_$g.log || exit 1
cp $T/parent_trunk_grt.tcl $N/ptgrt.tcl
docker run --rm --name qc18-inc-$D-$g --cpus=4 --memory=16g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; MODE=inc DPL=1 ECO=/w/eco_$g.tcl CORNER=TT ODB=/w/g_$p.odb OUT=/w/arrx_$g.txt ODB_OUT=/w/g_$g.odb openroad -threads 4 -exit /w/ptgrt.tcl; echo EXIT \$?" > inc_$g.log 2>&1
grep -q "EXIT 0" inc_$g.log || { echo inc fail; exit 1; }
for C in TT FF; do docker run --rm --name qc18-m-$D-$g-$C --cpus=2 --memory=12g -v $P:/p:ro -v $N:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; MODE=inc CORNER=$C ODB=/w/g_$g.odb OUT=/w/arr_${g}_$C.txt openroad -threads 2 -exit /w/ptgrt.tcl; echo EXIT \$?" > m_${g}_$C.log 2>&1 & done; wait
grep -h EXIT m_${g}_TT.log m_${g}_FF.log | tr "\n" " "
python3 -I $T/parent_trunk_dme.py ocv trunk_${g}_built.json arr_${g}_TT.txt arr_${g}_FF.txt ocv_$g.json > /dev/null && python3 -c "import json;o=json.load(open(\"ocv_$g.json\"));print(\"$D $g\", {C:(o[C][\"nominal_spread\"],o[C][\"ocv_inclusive_spread\"]) for C in o}, open(\"eco_$g.log\").read().strip()[-120:])"
echo "stepi $D $g done $(date)"
