#!/bin/bash
# Q-VMWB: build the 8 bench variants in parallel and run every shipped decoder ME result op on each.
# usage (inside the source tree): run_all.sh OUT
set -u
R=$(cd "$(dirname "$0")/../.." && pwd); cd "$R"; O=$(mkdir -p "$1" && readlink -f "$1")
D=results/arch/qwen_split_compute_1014/vmwb_1015
CFGS="pos:-GVARIANT=1 base:-GVARIANT=0 o3:-GVARIANT=1,-GIMUT=2 smut1:-GVARIANT=1,-GSMUT=1 smut2:-GVARIANT=1,-GSMUT=2 imut1:-GVARIANT=1,-GIMUT=1 imut3:-GVARIANT=1,-GIMUT=3 vpmut1:-GVARIANT=1,-GVPMUT=1"
for c in $CFGS; do n=${c%%:*}; a=$(echo ${c#*:} | tr , ' '); ( J=12 bash tools/qwen_vmwb/build_bench.sh "$O/b_$n" $a -GTE=13; echo "$n build rc=$?" ) & done; wait
for c in $CFGS; do n=${c%%:*}; [ -x "$O/b_$n/obj/Vtb_vmwb" ] || continue
  while read -r pc args; do echo "$n $pc $("$O/b_$n/obj/Vtb_vmwb" $args 2>&1 | grep -E '^\{|^PASS|^FAIL vmwb' | tr '\n' ' ')"; done < $D/pcs.txt
done | tee "$O/results.txt"
