#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
N=/srv/opentallas-scratch2/claude/codex-kv-boot-2005
cd "$N/build"
while read -r P; do
  echo "REBUILD_PC $P $(date -Is)"
  make -f obj/Vtb_kvslice_hier.mk hier_launch_verilator VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/${P}__hierMkArgs.f" > "$P.verilate.log" 2>&1
  make -C "obj/$P" -f "$P.mk" -j12 "VM_PREFIX=$P" > "$P.make.log" 2>&1
done < <(python3 -c 'import json; print("\n".join(json.load(open("../pc_libs.json"))))')
echo "TOP_FRONTEND $(date -Is)"
make -f obj/Vtb_kvslice_hier.mk hier_launch_verilator VM_HIER_LAUNCH_VERILATOR_ARGSFILE=obj/Vtb_kvslice__hierMkArgs.f > top_verilate.log 2>&1
make -C obj -f Vtb_kvslice.mk -j12 > top_make.log 2>&1
echo "BUILD_DONE $(date -Is)"
I=/srv/opentallas-scratch2/claude/tok-qk-b48/inputs
mkdir -p "$N/nominal" "$N/mut_frame"
for mode in nominal mut_frame; do
  cd "$N/$mode"
  ln -sfn /srv/opentallas-scratch2/claude/wt/codex-kv-pv-image-0733/physical physical
  args=(); [ "$mode" = nominal ] || args+=(+MUT_FRAME=100)
  set +e
  /usr/bin/time -v stdbuf -oL "$N/build/obj/Vtb_kvslice" +PHASE=boot +FRAMES="$I/frames.hex" +EXPECT="$I/expect.txt" +EPOCH=2827 +START_AFTER_SETUP "${args[@]}" >sim.log 2>time.log
  rc=$?
  set -e
  echo "$rc" > exit
  echo "$mode rc=$rc $(grep -m1 KVSLICE_BOOT sim.log)"
done
