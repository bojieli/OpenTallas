#!/bin/bash
# NEGATIVE-control root: the OLD TYPE-SAFE-5 kits (no 477d2ed), hard-link copy of TOK-VERIFY-1 a2/froot + its schedules
set -eu
V=/srv/opentallas-scratch2/claude/tok-verify-1; D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; C=$D/code
cd /
[ -d $D/root_old ] || cp -al $V/a2/froot $D/root_old
for M in col_h9 col_h10; do
  P=$D/root_old/rtl/dsrom_sys/s81_dv/frame_lp/plan/${M}_l4_lp_plan_kit.sv
  E=$D/root_old/ext/srv/opentallas-scratch2/claude/type-safe-4/s81p3/romq_rtl/${M}_l4_lp_plan_kit.sv
  cmp -s $P $E || { rm -f $P; ln $E $P; }
  sha256sum $P | cut -c1-16
done
mkdir -p $D/sched_old && cp -p $V/a2/fsa/*/*_schedule.json $V/a2/fsa/*/*_check.json $D/sched_old/ && cp -p $D/sched/gb_provider_qualification.json $D/sched_old/
mkdir -p $D/runs_old
for M in col_h9 col_h10; do O=$D/runs_old/${M}_asb_x; [ -d $O ] && continue
  python3 -I $C/tools/s81_dv/bf_asbuilt_1101/prepare.py --source $D/root_old --schedule $D/sched_old/${M}_l4_lp_asb_x_schedule.json \
    --out $O --master $M --variant asb_x --native-bf-family --defines-manifest physical/die_plan/s81/bind/frame_asbuilt.json; echo "PREP_OLD $M rc=$?"
done
