#!/bin/bash
# usage: lockstep.sh <core>   (inside ot-run) legacy vs __q3sync lockstep sim
set -u
core=$1
WT=$(git rev-parse --show-toplevel) || exit 2
S=${OUTROOT:?set OUTROOT to a fresh run directory}
cd "$WT"
[ -n "$(git status --porcelain --untracked-files=no)" ] && { echo "DIRTY tracked tree: refuse"; exit 2; }
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
CEN=$WT/tools/hbm_b2/q3sync/cohort.json
D=$S/lockstep_$core; rm -rf $D; mkdir -p $D
read src top < <(python3 -c "import json;t=json.load(open('$CEN'))['totals_per_core']['$core'];print(t['source'],t['legacy_top'])")
python3 -I $WT/tools/hbm_b2/q3sync/q3_lockstep_tb.py $WT/$src $top --out $D/tb.sv --hold ${HOLD:-64} --cycles ${CYCLES:-4000}
gen=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join('$S/gen/'+f for f in c['core_filelists']['$core']['files']))")
leg=$(python3 -c "
import json;c=json.load(open('$CEN'));fl=set(c['core_filelists']['$core']['files'])
print(' '.join('$WT/'+e['source'] for e in c['emitted'] if e['emitted'] in fl))")
mac=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join('$WT/'+m for m in c['core_filelists']['$core']['macros']))")
log=$S/lint/lockstep_${core}.log
echo "# $(date) host=$(hostname) commit=$(git -C $WT rev-parse HEAD) dirty_tracked=$(git -C $WT status --porcelain --untracked-files=no -- rtl physical tools | wc -l) core=$core" > $log
$V --binary --timing -j 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --Mdir $D/obj --top-module tb $D/tb.sv $leg $gen $mac >> $D/build.log 2>&1
brc=$?; echo "# build rc=$brc" >> $log
[ $brc = 0 ] && { $D/obj/Vtb >> $log 2>&1; echo "# sim rc=$? $(date)" >> $log; }
tail -3 $D/build.log >> $log
