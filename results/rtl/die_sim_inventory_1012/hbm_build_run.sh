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
st "v3 builds+runs start src ca7ca4fff"
SUP="--g SU_N=512 --g SU_M=128 --g SU_LV=6 --g SU_WIDE=1 --g FUSED_UWIDE=1 --g FUSED_UN=64 --g FUSED_UM=16"
mk(){ n=$1; d=$2; shift 2; python3 $SRC/tools/hgi_e2e/run.py script --vehicle X "$@" --out $G/b_$n.sh >/dev/null && sed -i '/^set +e/,$d' $G/b_$n.sh && \
  { [ -z "$d" ] || sed -i "s|--top-module tb_hgi_e2e|+define+$d --top-module tb_hgi_e2e|" $G/b_$n.sh; } && \
  ( SRC=$SRC VEC=$G/vec OUT=$G/bld/$n VERILATOR=$VER cap 150 3h bash $G/b_$n.sh; echo "build $n rc=$?" >> $LOG ) ; }
mk idxn    "" --real idxn &
mk idxnmut "" --real idxn --g IDX_MUT=2 &
mk dsall   "" --real coll,dma,fused,idxn,quant,sfu,su $SUP &
wait
mk dsallmut "" --real coll,dma,fused,idxn,quant,sfu,su $SUP --g DMA_MUT=5 &
mk coll    "" --real coll &
mk collmut OT_COLL_AMX_MUT_MIN --real coll &
wait
mk qall    "" --real coll,dma,fused,sfu,su $SUP &
mk qallmut "" --real coll,dma,fused,sfu,su $SUP --g DMA_MUT=5 &
wait; st "builds done"
until [ -f $G/vec/READY ]; do sleep 60; done; st "vectors ready"
run(){ c=$1; v=$2; B=$(ls $G/bld/$c/*/obj/tb 2>/dev/null | head -1); O=$G/out/${c}__$v; mkdir -p $O
  [ -x "$B" ] && [ -f $G/vec/$v/prep.txt ] || { echo "$(date '+%T') run $c $v SKIP (no binary or vector)" >> $G/STATUS.log; return; }
  s=$(date +%s)
  ( cd $O && cap 4 6h $B +DIR=$G/vec/$v +OUT=$O/e2e_records.txt > $O/run.log 2>&1; echo "rc=$?" >> $O/run.log )
  python3 $SRC/tools/hgi_e2e/run.py report $O --out $O/report.json > $O/report.log 2>&1
  echo "$(date '+%T') run $c $v $(( $(date +%s)-s ))s $(grep -m1 -oE 'HGI_E2E[^\n]{0,60}' $O/run.log | head -c 80) $(tail -1 $O/run.log)" >> $G/STATUS.log; }
export -f run
( for L in 0 1 2 3 14 20 21 24 37; do echo "idxn ds_L$L"; echo "dsall ds_L$L"; done
  echo "idxnmut ds_L24"; echo "dsallmut ds_L20"; echo "coll ds_head"; echo "collmut ds_head"; echo "qall qwen_L0"; echo "qallmut qwen_L0" ) | xargs -P 24 -L1 bash -c 'run $0 $1'
st "ALL DONE"
