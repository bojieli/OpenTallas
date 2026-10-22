#!/bin/bash
# KV-BIND12 head safe32 geometry check: before (the run tree a34df2a74) / after (overlay = run tree + this branch's files)
set -u
D=/srv/opentallas-scratch/claude/kv-bind12-head
ORIG=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-a34df2a74-gen9d15p
FL=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-a34df2a74-gen9d15p/kv_flags.env
OV=$D/ov
if [ ! -d $OV ]; then
  mkdir -p $OV
  for e in $ORIG/* $ORIG/.[!.]*; do b=$(basename $e); [ "$b" = tools ] || [ "$b" = results ] || ln -s $e $OV/$b; done
  mkdir -p $OV/tools $OV/results/arch
  for e in $ORIG/tools/*; do b=$(basename $e); [ "$b" = qwen_kv_die ] || ln -s $e $OV/tools/$b; done
  cp -r $ORIG/tools/qwen_kv_die $OV/tools/qwen_kv_die
  for e in $ORIG/results/*; do b=$(basename $e); [ "$b" = arch ] || ln -s $e $OV/results/$b; done
  for e in $ORIG/results/arch/*; do b=$(basename $e); [ "$b" = qwen_kv_die ] || ln -s $e $OV/results/arch/$b; done
  mkdir -p $OV/results/arch/qwen_kv_die
  for e in $ORIG/results/arch/qwen_kv_die/*; do ln -s $e $OV/results/arch/qwen_kv_die/$(basename $e); done
fi
tar -C $OV -xf $D/branch.tar
set -a; . $FL; set +a
[ -s $D/geom_before.json ] || ( cd $ORIG && TAG=before timeout 3000 python3 $D/geom.py ) > $D/geom_before.json 2> $D/geom_before.err; echo "before exit $?"
( cd $OV && TAG=after_6x3 timeout 3000 python3 $D/geom.py ) > $D/geom_after.json 2> $D/geom_after.err; echo "after exit $?"
if [ -d $OV/results/arch/qwen_kv_die/head_safe32/alt_5x4 ]; then
( cd $OV && TAG=alt_5x4 OT_KV_QKH_SAFE32_PLANS=results/arch/qwen_kv_die/head_safe32/alt_5x4 timeout 3000 python3 $D/geom.py ) > $D/geom_alt.json 2> $D/geom_alt.err; echo "alt exit $?"
fi
