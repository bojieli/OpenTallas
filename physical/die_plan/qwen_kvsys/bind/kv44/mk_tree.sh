#!/bin/bash
# mk_tree.sh REV OUT : bind source tree = e33504a6f (src_e335, hardlinked) + REV's tools/die_plan, physical/die_plan,
# rtl/qwen_sys/kv_plan_leaves_1023, rtl/lib/ot_dp_*.sv (overlay files are unlinked first, never written through a hardlink)
set -euo pipefail
REV=$1; OUT=$2; S=/srv/opentallas-scratch2/claude/kv/kvbind
[ -e $OUT ] && { echo "$OUT exists"; exit 2; }
cp -al $S/src_e335 $OUT
cd ~/OpenTallas
P="tools/die_plan physical/die_plan rtl/qwen_sys/kv_plan_leaves_1023 $(git ls-tree --name-only $REV rtl/lib/ | grep -E '^rtl/lib/ot_dp_' | tr '\n' ' ')"
rm -rf $OUT/tools/die_plan $OUT/physical/die_plan
T=$(mktemp -d $S/ovl.XXXX); git archive $REV $P | tar -x -C $T; rsync -a $T/ $OUT/; rm -rf $T
echo "$REV" > $OUT/OVERLAY_REV; echo "$P" >> $OUT/OVERLAY_REV
echo "tree $OUT = e33504a6f + $REV overlay"
