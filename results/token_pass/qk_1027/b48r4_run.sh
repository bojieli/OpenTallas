#!/bin/bash
# TOK-QK r4: resume Codex codex-kv-boot-2005 B48 native boot after its top C++ make failed (spill omitted .cpp/.o of 56 unchanged hier libs; relinked to build3/obj like stage.py intended). No source change.
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
N=/srv/opentallas-scratch2/claude/codex-kv-boot-2005
R=/srv/opentallas-scratch2/claude/tok-qk-b48r4
cd "$N/build"
echo "TOP_MAKE $(date -Is)"
make -C obj -f Vtb_kvslice.mk -j12 > $R/top_make.log 2>&1
echo "BUILD_DONE $(date -Is)"
I=/srv/opentallas-scratch2/claude/tok-qk-b48/inputs
for mode in nominal mut_frame; do
  mkdir -p "$R/$mode"; cd "$R/$mode"
  ln -sfn /srv/opentallas-scratch2/claude/wt/codex-kv-pv-image-0733/physical physical
  args=(); [ "$mode" = nominal ] || args+=(+MUT_FRAME=100)
  set +e
  /usr/bin/time -v stdbuf -oL "$N/build/obj/Vtb_kvslice" +PHASE=boot +FRAMES="$I/frames.hex" +EXPECT="$I/expect.txt" +EPOCH=2827 +START_AFTER_SETUP "${args[@]}" >sim.log 2>time.log
  rc=$?
  set -e
  echo "$rc" > exit
  echo "$mode rc=$rc $(grep -m1 KVSLICE_BOOT sim.log) $(date -Is)"
done
