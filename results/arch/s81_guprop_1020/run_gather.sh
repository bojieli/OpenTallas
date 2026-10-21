#!/bin/bash
# DRIVE-S81-GUPROP 10-20: gate/up gather map + check (tools/s81_dv/layer_prog/gu_gather.py) on the column-reduced inventory,
# campaign env of DENSE2 run_cap.sh.  usage: run_gather.sh DROPFC GU_PROP OUTNAME [ROOT(root)]
#   98 frames = DROPFC 3R,4L ; 84 frames = DROPFC 1R,3R,4L,6L (ROW0 1)
set -uo pipefail; cd "$(dirname "$0")"
R=${4:-root}
export OT_SVCPLAN_DROPFC=$1 OT_SVCPLAN_ROW0=1 OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 OT_XS_GU_PROP=$2 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH OT_XS_DENSE_SPLIT2 OT_XS_DENSE_SPLIT2_ROWS
# capacity_cols.py imports root/tools/s81_dv/layer_prog: run it from a dir whose root/ is $R
D=$PWD; [ "$R" = root ] || { D=$(mktemp -d); ln -s $(realpath $R) $D/root; cp capacity_cols.py $D/; }
PYTHONPATH=$D:$R/tools/s81_dv/layer_prog python3 $R/tools/s81_dv/layer_prog/gu_gather.py --cols --die-src dieref --fixtures fixtures/L0 --out $3.json > $3.log 2>&1
echo "GATHER_RC $?" >> $3.log; tail -2 $3.log | cut -c1-1500
