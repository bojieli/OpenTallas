#!/bin/bash
# diesim-1012 (scope v2): HBM native die e2e, one DS layer per type + head at P=1,048,575, Qwen L0 at P8191, current main ca7ca4fff.
set -u
G=/srv/opentallas-scratch/claude/diesim-1012/hbm; SRC=/srv/opentallas-scratch/claude/diesim-1012/src
mkdir -p $G/vec $G/out $G/logs $G/bld; cd $G
LOG=$G/STATUS.log; st(){ echo "$(date '+%F %T %Z') $*" >> $LOG; }
cap(){ m=$1; t=$2; shift 2; timeout $t systemd-run --user --scope -q -p MemoryMax=${m}G -p MemorySwapMax=0 -- "$@"; }
export -f cap
PY=/srv/opentallas-scratch/claude/qwen-hbm-unify/venv/bin/python
SNAP=/srv/opentallas-scratch/claude/qwen-hbm-unify/hfhome/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218
export NPY_DISABLE_CPU_FEATURES="AVX512F AVX512CD AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL AVX512_SPR AVX512_KNL AVX512_KNM" OT_V41_FLASH_SNAPSHOT=/srv/opentallas-scratch/claude/hbm-sim/ds_ckpt HDC_V41_ARITH=chunk8
export G SRC PY SNAP
VER=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
st "v3 exports start src ca7ca4fff"
ex(){ v=$1; case $v in
  ds_head) a="ds --refs /home/ubuntu/w17work/ref/ctx1048576_seed20260930 --layer 39 --head";;
  ds_*) a="ds --refs /home/ubuntu/w17work/ref/ctx1048576_seed20260930 --layer ${v#ds_L} --iks";;
  qwen_*) a="qwen --snapshot $SNAP --cache /srv/opentallas-scratch/claude/hbm-sim/qimg --layer ${v#qwen_L} --position 8191";; esac
  rm -rf $G/vec/$v
  ( cd $SRC/tools && cap 80 3h $PY -m hgi_e2e.export $a --out $G/vec/$v > $G/logs/exp_$v.log 2>&1 ) && \
  python3 $SRC/tools/hgi_e2e/run.py prep $G/vec/$v > $G/logs/prep_$v.log 2>&1; echo "$(date '+%T') export $v rc=$?" >> $G/STATUS.log; }
export -f ex
echo ds_L0 ds_L1 ds_L2 ds_L3 ds_L14 ds_L20 ds_L21 ds_L24 ds_L37 ds_head qwen_L0 | tr ' ' '\n' | xargs -P 5 -I{} bash -c 'ex {}'
wait
touch $G/vec/EXPORTS_DONE; st "exports done"
