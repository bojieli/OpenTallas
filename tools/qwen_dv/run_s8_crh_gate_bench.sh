#!/usr/bin/env bash
set -euo pipefail
out=$1
mode=$2
mkdir -p "$out"
srcs=(rtl/qwen_dv/s5/s8/qfd_dv_s8_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/test/qwen_dv/s8/tb_rp1_crh.sv)
case "$mode" in
 primary) ;;
 bank) sed "s/wire rp_bk=rp_k\[0\];/wire rp_bk=~rp_k[0];/" "${srcs[0]}" > "$out/bankswap.sv";srcs[0]="$out/bankswap.sv" ;;
 mask) sed 's/twc_crw \&\& (!twc_half\[1\] || twc_half\[0\] == bk\[0\])/twc_crw/' "${srcs[1]}" > "$out/fullwrite.sv";srcs[1]="$out/fullwrite.sv" ;;
 *) echo 'unknown mutation' >&2; exit 2 ;;
esac
iverilog -g2012 -s tb_rp1_crh -o "$out/run" "${srcs[@]}" > "$out/build.log" 2>&1
vvp "$out/run"
