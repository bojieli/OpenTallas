#!/bin/bash
# rom-layer-tput-qwen 10-13: same vehicle, VM x-read transport XVM 1 -> 11 (+10 edges per x read, the TP8 bit-plane VM hand-off)
set -u
G=/srv/opentallas-scratch/claude/rom-layer-tput-qwen/bd6e82288; SRC=$G/src; cd $G
st(){ echo "$(date '+%F %T %Z') $*" >> $G/STATUS.log; }
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export QWEN_FX="/srv/opentallas-scratch/claude/token-exact"
export QWEN_FX_HISTORY=$QWEN_FX/fx/history QWEN_FX_GOLD=$QWEN_FX/gold/tp4_hs/P8191 QWEN_FX_REF=$QWEN_FX/gold/tp4_hs/oracle.json
export PATH=$(dirname $VERILATOR):$PATH QROM_OPTRACE=1 RT_OPTRACE=1 QROM_XVM=11 QROM_BD=51
A="--variant part --dcu 2 --duc 2 --su-ml 7"; n=qrom_xvm11bd51
( cd $SRC && ot-heavy --mem 48 -- python3 tools/qwen_missing/partition_token.py build $A --comp 1 --build $G/bld/$n --jobs 32 ) > $G/logs/build_$n.log 2>&1; rc=$?; st "build $n rc=$rc"
[ $rc = 0 ] && { ( cd $SRC && ot-heavy --mem 24 -- python3 tools/qwen_missing/partition_token.py run $A --comp 1 --build $G/bld/$n --work $G/out/${n}__L3 --stages L3 --threads 32 ) > $G/logs/${n}__L3.log 2>&1; st "run $n rc=$?"; }
st "XVMBD DONE"; touch $G/XVMBD_DONE
