#!/bin/bash
# QW-DIEFIX-NFAR: prep (cid 2, 3, 3 swap 48/49) + mask sets, then build+run variant $1
set -u
W=/srv/opentallas-scratch/claude/qw-diefix-xt1n; cd $W
B=$W/src/rtl/test/qwen_dv/xhead
IMG=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/stage/img/L0/die0
FX=/srv/opentallas-scratch/claude/qw-realstg/fx
V=$1
if [ "$V" = fixed ]; then
  for c in 2 3; do [ -f prep_c$c/gold.json ] || python3 $B/xt1_prep.py --img $IMG --fx $FX --cid $c --out prep_c$c > prep_c$c.log 2>&1 || { echo PREP_FAIL c$c; cat prep_c$c.log; exit 4; }; done
  [ -f prep_c3swap/gold.json ] || python3 $B/xt1_prep.py --img $IMG --fx $FX --cid 3 --swap 48,49 --out prep_c3swap > prep_c3swap.log 2>&1 || { echo PREP_FAIL swap; exit 4; }
  mkdir -p masks_fixed masks_swap
  ln -sf $W/prep_c2/masks/* masks_fixed/; ln -sf $W/prep_c3/masks/* masks_fixed/
  ln -sf $W/prep_c2/masks/* masks_swap/; ln -sf $W/prep_c3swap/masks/* masks_swap/
  touch prep.done
  cat prep_c2.log prep_c3.log
  bash $B/run_xt1n.sh $W fixed nominal:8:4 nominal:4:2 romswap:8:4:masks_swap
else
  while [ ! -f prep.done ]; do sleep 30; done
  bash $B/run_xt1n.sh $W oldtags nominal:8:4
fi
