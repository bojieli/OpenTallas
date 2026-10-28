#!/bin/bash
# DIE-HBM/KITS: shared kit_preflight on every generated kit under KITDIR (receipt never overwritten)
#   pf_all.sh PLANDIR KITDIR PFDIR WT
P=$1; K=$2; D=$3; W=$4; mkdir -p $D
one() { k=${1%/}; n=$(basename $k); [ -f $D/$n.json ] && return 0; [ -f $k/freeze.json ] || return 0
  ( cd $W/tools/die_plan && timeout 1200 python3 kit_preflight.py --plan-dir $P --out $D/$n.json $k > $D/$n.txt 2>&1 )
  echo "$n $(head -1 $D/$n.txt)"; }
export -f one; export P D W
ls -d $K/*/ | xargs -P 4 -I{} bash -c 'one {}'
