#!/usr/bin/env bash
set -euo pipefail
out=${1:-bench_s8_rp1}
mkdir -p "$out"
srcs=(rtl/qwen_dv/s5/s8/qfd_dv_s8_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/test/qwen_dv/s8/tb_rp1_crh.sv)
iverilog -g2012 -s tb_rp1_crh -o "$out/primary" "${srcs[@]}" > "$out/build.log" 2>&1
vvp "$out/primary" > "$out/primary.log" 2>&1
# Mutants preserve the actual source in the immutable snapshot.
sed "s/wire rp_bk=rp_k\[0\];/wire rp_bk=~rp_k[0];/" "${srcs[0]}" > "$out/bankswap.sv"
iverilog -g2012 -s tb_rp1_crh -o "$out/mut_bank" "$out/bankswap.sv" "${srcs[@]:1}" > "$out/build_bank.log" 2>&1
if vvp "$out/mut_bank" > "$out/bank.log" 2>&1;then echo 'BANK MUTANT ESCAPED';exit 1;fi
sed 's/twc_crw \&\& (!twc_half\[1\] || twc_half\[0\] == bk\[0\])/twc_crw/' "${srcs[1]}" > "$out/fullwrite.sv"
iverilog -g2012 -s tb_rp1_crh -o "$out/mut_full" "${srcs[0]}" "$out/fullwrite.sv" "${srcs[@]:2}" > "$out/build_full.log" 2>&1
if vvp "$out/mut_full" > "$out/full.log" 2>&1;then echo 'FULLWRITE MUTANT ESCAPED';exit 1;fi
cat "$out/primary.log" "$out/bank.log" "$out/full.log"
echo 'PASS both expected mutants caught'
