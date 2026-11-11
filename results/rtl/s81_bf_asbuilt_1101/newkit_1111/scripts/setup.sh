#!/bin/bash
# S81-FRAME-FIX-1 / BF as-built measurement 11-11: own dirs on intel1 (hard-link copies; nothing of TOK-VERIFY-1 edited)
set -eu
V=/srv/opentallas-scratch2/claude/tok-verify-1
D=/srv/opentallas-scratch2/claude/s81-bfasb-1111
mkdir -p $D
cd /
[ -d $D/root ] || cp -al $V/b3/froot $D/root
[ -d $D/code ] || cp -al $V/wt_b $D/code
# the .git file of the copied worktree must not point git at TOK-VERIFY's repo from here
[ -f $D/code/.git ] && rm -f $D/code/.git
# rtl plan-kit path -> main ef870e kits (the root's ext/ copy is the manifest/schedule entry; same bytes)
for M in col_h9 col_h10; do
  P=$D/root/rtl/dsrom_sys/s81_dv/frame_lp/plan/${M}_l4_lp_plan_kit.sv
  E=$D/root/ext$V/b3/kits/${M}_l4_lp_plan_kit.sv
  cmp -s $P $E || { rm -f $P; ln $E $P; }
  sha256sum $P $E $D/code/rtl/dsrom_sys/s81_dv/frame_lp/plan/${M}_l4_lp_plan_kit.sv | cut -c1-16
done
mkdir -p $D/sched && cp -p $V/b3/sched/* $D/sched/
ls $D
