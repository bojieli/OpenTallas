#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?outputdir};images=${2:?actual image root};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
sources=(rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" "$d/ot_hbm_svc_prefetch_mapped4_cdc.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/chip/ot_chip_v41x_hbm3e_phy.sv "$d/tb_hbm_svc_prefetch_mapped4_checkpoint.sv")
for stack in 0 1;do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_mapped4_checkpoint -GSTACK=$stack --Mdir "$out/obj$stack" -o positive "${sources[@]}" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv" > "$out/build$stack.log" 2>&1
 first=$((8*stack));last=$((first+7));if ((last>12));then last=12;fi
 for ((sm=first;sm<=last;sm++));do
  printf -v name 'sm%02d' "$sm"
  tag=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["tag_base"])' "$images/$name/config.json")
  "$out/obj$stack/positive" +DIR="$images/$name" +SM="$sm" +TAGBASE="$tag" > "$out/$name.log"
  grep -q 'MAPPED4_CHECKPOINT PASS' "$out/$name.log"
 done
done
sed 's/kr_beat\[1:0\]\^row_low_q\[ret\]/kr_beat[1:0]/' "$d/ot_hbm_svc_prefetch_mapped4_owner.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv";then exit 1;fi
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_mapped4_checkpoint -GSTACK=0 --Mdir "$out/mutant_obj" -o mutant "${sources[@]}" "$out/mutant.sv" > "$out/mutant_build.log" 2>&1
if "$out/mutant_obj/mutant" +DIR="$images/sm00" +SM=0 +TAGBASE=1000 > "$out/mutant.log";then echo 'mapped burst permutation mutant passed';exit 1;fi
grep -q 'checkpoint actual sector mismatch' "$out/mutant.log"
cat "$out"/sm??.log
echo 'MAPPED4_CHECKPOINT_MUTANT rejected actual row/burst permutation error'
