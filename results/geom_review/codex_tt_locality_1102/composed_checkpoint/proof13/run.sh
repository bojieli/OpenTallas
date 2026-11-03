#!/bin/bash
set -uo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
bad=0
for v in prod late reset; do
 yosys -Q -T -s /work/proof13_outputs/$v.ys > /work/proof13_outputs/$v.log 2>&1
 rc=$?
 echo "NATIVE_REGIONAL_PROOF $v rc=$rc"
 if [[ $v == prod && $rc != 0 ]] || [[ $v != prod && $rc == 0 ]]; then bad=1; fi
done
exit $bad
