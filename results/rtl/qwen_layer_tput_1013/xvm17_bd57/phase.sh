#!/bin/bash
set -eu
root=/srv/opentallas-scratch/claude/codex-takeover-1013/qwen-vm-probes
name=$1;phase=$2
case "$name" in
 x14_pos) xvm=15;bd=55;comp=1;stages=L3;;
 x14_mut) xvm=15;bd=55;comp=0;stages=L0;;
 x16_pos) xvm=17;bd=57;comp=1;stages=L3;;
 x16_mut) xvm=17;bd=57;comp=0;stages=L0;;
 *) exit 2;;
esac
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export QWEN_FX=/srv/opentallas-scratch/claude/token-exact
export QWEN_FX_HISTORY=$QWEN_FX/fx/history QWEN_FX_GOLD=$QWEN_FX/gold/tp4_hs/P8191 QWEN_FX_REF=$QWEN_FX/gold/tp4_hs/oracle.json
export PATH="$(dirname "$VERILATOR"):$PATH" QROM_OPTRACE=1 RT_OPTRACE=1 QROM_XVM=$xvm QROM_BD=$bd
cd "$root/src"
if [ "$phase" = build ]; then
 python3 tools/qwen_missing/partition_token.py build --variant part --dcu 2 --duc 2 --su-ml 7 --comp "$comp" --build "$root/build/$name" --jobs 32
elif [ "$phase" = run ]; then
 python3 tools/qwen_missing/partition_token.py run --variant part --dcu 2 --duc 2 --su-ml 7 --comp "$comp" --build "$root/build/$name" --work "$root/out/$name" --stages "$stages" --threads 32
else exit 2
fi
