#!/bin/bash
# TOK-QK-KVL 10-27 smoke on the B48 r4 binary (old far end: one +VEC for every layer): boot, then layer 0 of the token
# with the d0_g0 head's layer-0 operands and layer-0 HBM history (--skip-last); POST covers L0 only.  Checks the token
# phase + operand conventions before the per-layer build lands.  Layers >= 1 are out of scope here (no history preloaded).
set -u
K=/srv/opentallas-scratch2/claude/tok-qk-kvl; B=/srv/opentallas-scratch2/claude/codex-kv-boot-2005/build/obj/Vtb_kvslice
I=/srv/opentallas-scratch2/claude/tok-qk-b48/inputs; PHYS=/srv/opentallas-scratch2/claude/wt/codex-kv-pv-image-0733/physical
O=$K/smoke_old; mkdir -p $O; cd $O; ln -sfn $PHYS physical
V=$K/vec/L0_d0_g0
/usr/bin/python3 $K/kv_preload.py --kv $V/kv.hex --ctx 8192 --asbuilt $PHYS/die_plan/qwen_kvsys/bind/asbuilt_map.json --layers 0 --skip-last > preload.txt 2> preload.log || exit 2
/usr/bin/time -v stdbuf -oL $B +PHASE=boot +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$(cat $I/epoch.txt) +START_AFTER_SETUP   +FAR=1 +VEC=$V +CTX=8192 +POST=${POST:-16000} +HBM_LOG=16 +HBM_PRELOAD=$O/preload.txt > sim.log 2> time.log
echo $? > exit; grep -m1 '^KVSLICE_BOOT' sim.log | cut -c1-60; grep '^FAR_SUMMARY\|^FAR_RESULT_MISMATCH\|^FAR_FAULT' sim.log | head
