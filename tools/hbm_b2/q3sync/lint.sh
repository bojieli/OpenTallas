#!/bin/bash
# usage: lint.sh <gen|legacy> <core>   (run inside ot-run; writes logs under $OUT)
set -u
WT=$(git rev-parse --show-toplevel) || exit 2
S=${OUTROOT:?set OUTROOT to a fresh run directory}
cd "$WT"
[ -n "$(git status --porcelain --untracked-files=no)" ] && { echo "DIRTY tracked tree: refuse"; exit 2; }
G=$S/gen
OUT=$S/lint; mkdir -p $OUT
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mode=$1; core=$2
CEN=$WT/tools/hbm_b2/q3sync/cohort.json
top=$(python3 -c "import json;t=json.load(open('$CEN'))['totals_per_core']['$core'];print(t['top'] if '$mode'=='gen' else t['legacy_top'])")
if [ $mode = gen ]; then
  files=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join('$G/'+f for f in c['core_filelists']['$core']['files']))")
else
  files=$(python3 -c "
import json;c=json.load(open('$CEN'));fl=set(c['core_filelists']['$core']['files'])
print(' '.join('$WT/'+e['source'] for e in c['emitted'] if e['emitted'] in fl))")
fi
macros=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join('$WT/'+m for m in c['core_filelists']['$core']['macros']))")
log=$OUT/${core}_${mode}.log
md=$S/lint/obj_${core}_${mode}; mkdir -p $md
echo "# $(date) mode=$mode core=$core top=$top host=$(hostname) commit=$(git -C $WT rev-parse HEAD) dirty_tracked=$(git -C $WT status --porcelain --untracked-files=no -- rtl physical tools | wc -l)" > $log
echo "# $V --lint-only -Wno-fatal -Werror-SELRANGE -Werror-WIDTH -Wno-TIMESCALEMOD --top-module $top $files $macros" >> $log
/usr/bin/time -v $V --lint-only -Wno-fatal -Werror-SELRANGE -Werror-WIDTH -Wno-TIMESCALEMOD --error-limit 1000000 --Mdir $md --top-module $top $files $macros >> $log 2>&1
rc=$?
echo "# rc=$rc $(date)" >> $log
echo "$core $mode rc=$rc" >> $OUT/rc.txt
exit $rc
