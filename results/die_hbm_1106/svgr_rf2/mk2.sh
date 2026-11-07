#!/bin/bash
# mk2.sh NAME STALL(0/1) MUT : bench tree src_NAME = src_rf1 (HBM-GAPS-5-LEC) with the resolved RF2 split in place of the RF1 split.
set -e; N=$1; ST=$2; M=$3
S=/srv/opentallas-scratch2/claude/hbm-gaps-5-lec/bench; B=/srv/opentallas-scratch2/claude/die-hbm-82-svgr/bench
G=rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv
rm -rf $B/src_$N; cp -a $S/src_rf1 $B/src_$N; rm -f $B/src_$N/$G
cp $B/r_rf2.sv $B/split_$N.sv
[ "$ST" = 1 ] && sed -i -f $S/stall_s1.sed $B/split_$N.sv
[ "$M" != 0 ] && sed -i "/^module ot_svgr_own #(/s/parameter integer MUT=0)(/parameter integer MUT=$M)(/" $B/split_$N.sv
python3 -I - $S/src_rf1/$G $S/tmp_rf1/split.sv $B/split_$N.sv $B/src_$N/$G <<'PY'
import sys
g=open(sys.argv[1]).read(); old=open(sys.argv[2]).read(); new=open(sys.argv[3]).read()
assert g.count(old)==1, g.count(old)
open(sys.argv[4],'w').write(g.replace(old,new))
PY
echo "tree $N stall=$ST mut=$(grep -c "MUT=$M)(" $B/split_$N.sv) stallbench=$(grep -c STALLBENCH $B/split_$N.sv)"
