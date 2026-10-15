#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
src=(rtl/qwen_sys/split_20261014/qkd_embgw_splitboot.sv rtl/qwen_sys/host_20261013/qkd_host_emb_boot_barrier.sv rtl/qwen_sys/host_20261013/qkd_host_boot_dispatch.sv rtl/qwen_sys/host_20261013/qkd_host_commit_order.sv)
for case in 'qkd_embgw_fresh_boot 6' 'qkd_host_emb_boot_barrier 1' 'qkd_host_boot_dispatch_lifecycle 2';do
 read -r name mutant <<< "$case";top="tb_$name";tb="rtl/test/qwen_host/$top.sv"
 iverilog -g2012 -s "$top" -o "$out/$name" "${src[@]}" "$tb"
 vvp "$out/$name" | tee "$out/$name-exact.log"
 iverilog -g2012 -s "$top" "-P$top.MUT=$mutant" -o "$out/$name-mut" "${src[@]}" "$tb"
 if vvp "$out/$name-mut" > "$out/$name-mutant.log" 2>&1;then echo "FAIL $name mutant escaped";exit 1;fi
 cat "$out/$name-mutant.log"
done
echo PASS SPLITBOOT_LIFECYCLE_COMPONENTS_EXACT_AND_MUTANTS
