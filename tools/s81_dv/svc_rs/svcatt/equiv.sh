#!/bin/bash
# equiv.sh DIR GOLD_TOP GATE_TOP : formal sequential equivalence of mapped gold flat.v vs bounded gate netlist
set -e
O=$1; G=$2; T=$3
LIB=/srv/opentallas-scratch/claude/elemsvc-g4-1021/out_norst/map/lib
cat > $O/equiv.ys <<YS
read_liberty -ignore_miss_func /tmp/lib/SIMPLE.lib
read_liberty -ignore_miss_func /tmp/lib/AO.lib
read_liberty -ignore_miss_func /tmp/lib/OA.lib
read_liberty -ignore_miss_func /tmp/lib/INVBUF.lib
read_liberty -ignore_miss_func /tmp/lib/SEQ.lib
read_verilog /o/flat.v
read_verilog /o/$(basename $4)
hierarchy -check
flatten
proc
opt_clean
async2sync
equiv_make $G $T equiv
hierarchy -top equiv
equiv_simple -seq 8
equiv_induct -seq 8
equiv_status -assert
YS
docker run --rm -v "$O:/o" -v "$LIB:/tmp/lib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /o/equiv.log -s /o/equiv.ys' > $O/equiv.out 2>&1 && echo EQUIV_PASS || { echo EQUIV_FAIL; tail -20 $O/equiv.log; }
