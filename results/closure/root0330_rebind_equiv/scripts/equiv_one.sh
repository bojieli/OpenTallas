#!/bin/bash
# equiv_one.sh <tile>: yosys equivalence of the old- vs new-variant elaborated (flattened) top
set -u
T=$1; R=$(cd "$(dirname "$0")" && pwd); D=$R/$T; O=$D/equiv; rm -rf $O; mkdir -p $O
TOP=$(python3 -c "import json;print(json.load(open('$R/index.json'))['$T']['top'])")
cat > $O/equiv.ys <<YS
read_rtlil $D/out_new/netlist.il
rename $TOP gate
design -stash gatedes
read_rtlil $D/out_old/netlist.il
rename $TOP gold
design -copy-from gatedes -as gate gate
async2sync
memory_map
opt_clean
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
YS
docker run --rm -v $R:$R -w $R openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/equiv.log -s $O/equiv.ys > /dev/null 2>&1
echo "exit=$?" > $O/status.txt
