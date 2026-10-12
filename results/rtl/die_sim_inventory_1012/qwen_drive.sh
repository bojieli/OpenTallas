#!/bin/bash
# diesim-1012 (scope v2): Qwen ROM die split partition (s22ml7: DCU 2 / DUC 2 / SU ML 7) at P8191 on current main ca7ca4fff:
# L3 chain (L0-L2, current K/V checked) positive + COMP 0 negative, and the LM head. Fixtures = token-exact 10-09 CPU golds.
set -u
G=/srv/opentallas-scratch/claude/diesim-1012/qwen; S=/srv/opentallas-scratch/claude/diesim-1012/src; B=/srv/opentallas-scratch/claude/token-exact
mkdir -p $G; cd $S; LOG=$G/STATUS.log
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export QWEN_FX_HISTORY=$B/fx/history QWEN_FX_GOLD=$B/gold/tp4_hs/P8191 QWEN_FX_REF=$B/gold/tp4_hs/oracle.json
cap(){ m=$1; t=$2; shift 2; timeout $t systemd-run --user --scope -q -p MemoryMax=${m}G -p MemorySwapMax=0 -- "$@"; }
K="--dcu 2 --duc 2 --su-ml 7"
for n in pos:1 neg:0; do v=${n%:*}; c=${n#*:}
  ( cap 128 4h python3 tools/qwen_missing/partition_token.py build --variant part $K --comp $c --build $G/build_$v --jobs 16 > $G/build_$v.log 2>&1
    echo "$(date '+%F %T') build $v rc=$?" >> $LOG ) &
done; wait
for j in "pos L3" "neg L3" "pos head"; do set -- $j
  ( s=$(date +%s); cap 48 6h python3 tools/qwen_missing/partition_token.py run --variant part $K --comp $([ $1 = pos ] && echo 1 || echo 0) \
      --build $G/build_$1 --work $G/run_$1_$2 --stages $2 --threads 16 > $G/run_$1_$2.log 2>&1
    echo "$(date '+%F %T') run $1 $2 rc=$? $(( $(date +%s)-s ))s $(tail -n 1 $G/run_$1_$2.log | cut -c1-250)" >> $LOG ) &
done; wait; echo "$(date '+%F %T') ALL DONE" >> $LOG
