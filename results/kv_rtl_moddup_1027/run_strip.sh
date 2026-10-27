#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/wt/kv-rtl-moddup-1027; D=/srv/opentallas-scratch2/claude/kv-rtl-moddup-1027
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator JOBS=4
cd $W; S=$D/strip; rm -rf $S; mkdir -p $S
for a in "pc 0" "pc 1" "pc 2" "kc 0" "kc 1"; do set -- $a
 ( bash physical/qkd_ctrl_strip/bench.sh $1 $S/$1m$2 $2 > $S/$1m$2.res 2>&1; echo "rc=$?" >> $S/$1m$2.res; rm -rf $S/$1m$2/obj_* ) &
done; wait; echo STRIPDONE > $S/done
