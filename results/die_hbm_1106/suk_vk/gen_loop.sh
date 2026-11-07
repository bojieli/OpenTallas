#!/bin/bash
R=/srv/opentallas-scratch2/claude/hbm-cons-2-suk; cd $R
for i in 1 2 3 4 5 6 7 8 9 10; do
  bash gen_vk_suk.sh $1 > logs/genloop_$1.out 2>&1 && { echo OK; tail -40 logs/genloop_$1.out | cut -c1-200; exit 0; }
  L=$(tail -1 logs/gen_ot_hbm_su_pg_lane_$1_x_core.log)
  miss=$(echo "$L" | sed -n "s#.*hbm-cons-2-suk/repo/\\([^' ]*\\).*#\\1#p" | head -1)
  [ -z "$miss" ] && { echo STOP; tail -6 logs/gen_ot_hbm_su_pg_lane_$1_x_core.log | cut -c1-500; tail -5 logs/genloop_$1.out; exit 1; }
  d=$(dirname "$miss"); echo add /$d; git -C repo sparse-checkout add /$d 2>&1 | tail -1
done
