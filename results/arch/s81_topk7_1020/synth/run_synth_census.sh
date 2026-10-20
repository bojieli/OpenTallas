#!/bin/bash
# S81-TOPK7 pre-gate admission (COORD 10-19 23:45): canonical ORFS synthesis of the HQ quarter (dsdv_bksel_q,
# -DOT_S81PH_SEL_HQ, the kit's reset landing + reset_relay_split 32 variables) and the MANDATORY native census
# (main 360c64320 tools/ref_tile/native_census.py) on the mapped netlist with the actual loaded Liberty.
# usage (on a fleet host, from the lane root L holding src/): run_synth_census.sh L TAG
set -u
L=$1; TAG=$2; R=$L/src; W=$L/$TAG; C=$R/results/arch/s81_topk7_1020/synth
mkdir -p $W/census; cp $C/config.mk $C/clock.sdc $W/
docker run --rm -v "$R:/src:ro" -v "$W:/work" openroad/orfs:asap7lock bash -lc \
  'cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > $W/synth.log 2>&1
echo SYNTH_RC=$?
N=$W/results/asap7/s81_topk7_hq/base/1_2_yosys.v
[ -s $N ] || { echo NO_NETLIST; tail -30 $W/synth.log; exit 2; }
sed -n 's/.*Executing Liberty frontend: //p' $W/logs/asap7/*/base/1*log | sort -u > $W/census/actual_liberties.txt
cp $C/native_census_main360c643.py $W/census/native_census.py; cp $C/textbook_lint_main360c643.py $W/census/textbook_lint.py
sha256sum $N $W/census/native_census.py > $W/census/inputs.sha256
docker run --rm -e PYTHONPATH=/w/census -v "$W:/w" openroad/orfs:asap7lock bash -lc 'set -eu; args=(); while IFS= read -r x; do args+=(--liberty "$x"); done < /w/census/actual_liberties.txt; x=; for a in "${args[@]}"; do x="$x $a"; done; python3 /w/census/native_census.py --netlist /w/results/asap7/s81_topk7_hq/base/1_2_yosys.v --top dsdv_bksel_q $x --out /w/census/native.json' > $W/census/native.log 2>&1 || echo NATIVE_RC=$?
python3 -c 'import json,sys;r=json.load(open(sys.argv[1]));print("CENSUS",r.get("status"),"max",r.get("max_dynamic_loads"),"viol",len(r.get("violations") or []),"roots",r.get("roots_examined"))' $W/census/native.json
grep -E "Number of cells|DFF|Chip area" $W/reports/asap7/s81_topk7_hq/base/synth_stat.txt 2>/dev/null | head -8
python3 $C/fanout_families.py $N > $W/census/families.txt 2>&1; grep FAM $W/census/families.txt | head -60
