#!/bin/bash
# run_one.sh <tile> <old|new>: elaborate the tile top (flow yosys, openroad/orfs:asap7lock) from its gate-bound SRCS
# (+ gate-bound `include files) plus the changed file(s) of variant old (gate-bound blob) / new (f722b4bbe blob)
set -u
T=$1; V=$2; R=$(cd "$(dirname "$0")" && pwd); D=$R/$T; O=$D/out_$V; rm -rf $O; mkdir -p $O
TOP=$(python3 -c "import json;print(json.load(open('$R/index.json'))['$T']['top'])")
CHP=$(python3 -c "import json;print(' '.join('-chparam %s %s'%tuple(p.split('=',1)) for p in json.load(open('$R/index.json'))['$T']['params']))")
INC=""; [ -d $D/inc ] && INC="-I$D/inc"
{
  for f in $(ls $D/src | sort); do echo "read_verilog -defer -sv -DSYNTHESIS $INC $D/src/$f"; done
  for f in $(ls $D/$V | sort); do echo "read_verilog -defer -sv -DSYNTHESIS $INC $D/$V/$f"; done
  echo "hierarchy -top $TOP $CHP"
  echo "tee -o $O/modules.txt ls"
  echo "proc; flatten; opt_clean -purge"
  echo "rename -enumerate"
  echo "tee -o $O/stat.txt stat"
  echo "write_rtlil $O/netlist.il"
  echo "write_verilog -noattr $O/netlist.v"
} > $O/script.ys
docker run --rm -v $R:$R -w $R openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/yosys.log -s $O/script.ys > /dev/null 2>&1
echo "exit=$?" > $O/status.txt
sha256sum $O/netlist.v 2>/dev/null | cut -d' ' -f1 > $O/netlist.sha256
if [ $V = new ] && [ -s $D/out_old/netlist.sha256 ] && [ -s $O/netlist.sha256 ]; then :; fi
