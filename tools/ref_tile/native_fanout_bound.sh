#!/bin/bash
# FLOW-CONSTFOLD 2026-10-21: run INSIDE the ORFS image (run_abi3_physical.native_fanout_bound).  Flatten the mapped
# netlist (Liberty cells -lib), tools/ref_tile/native_fanout_bound.py, write it back.  exit = the tool exit (0 written,
# 2 frontier, 3 no change).  usage: native_fanout_bound.sh NETLIST_IN NETLIST_OUT TOP REPORT "LIBS..." [TOOLDIR]
set -euo pipefail
IN=$1; OUT=$2; TOP=$3; REP=$4; LIBS=$5; T=${6:-/src/tools/ref_tile}
W=$(mktemp -d /tmp/nfb.XXXXXX); trap 'rm -rf "$W"' EXIT; RL=""; PL=""
for f in $LIBS; do b=$W/$(basename ${f%.gz}); if [[ $f == *.gz ]]; then zcat $f > $b; else cp $f $b; fi; RL="$RL read_liberty -lib $b;"; PL="$PL --liberty $f"; done
yosys -q -l $W/a.log -p "$RL read_verilog $IN; hierarchy -top $TOP; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; hierarchy -top $TOP; attrmap -remove src; attrmap -modattr -remove src; write_json $W/in.json"
set +e; python3 $T/native_fanout_bound.py $W/in.json $W/out.json --top $TOP --report $REP $PL ${NFB_FORCE:-}; rc=$?; set -e
if [ $rc -eq 0 ]; then
  yosys -q -l $W/b.log -p "read_json $W/out.json; hierarchy -top $TOP; write_verilog $OUT"
fi
exit $rc
