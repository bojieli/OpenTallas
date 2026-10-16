#!/bin/bash
# Q-ATTN-RATE 2026-10-15: production binary of the 16-row/cycle static native attention service.
# Same recipe as results/arch/qwen_attention_native_calendar_1015/build_zfix2.sh (real ECTL3 RL21/HXK8 lib, zfix static
# ASTK CTL lib, b4 EP/EX/ZN/head/AHUB/finalize/slice libs), with:
#  - cp lib = cp_fix.sv through gen_pv_rate.py --cp (4-port e read: qkd_astk_native_er_service_w, from source)
#  - parent = ot_qwen_tp8_attention_native_service_w16 (+ ot_qwen_tp8_pv_wide_pair from source, its 256 slices = the b4
#    ot_qwen_tp8_pv256_slice library) and tb_qwen_tp8_attention_native_service_w16; DMUT 0/1/2.
# Usage: build_w16.sh SRC_DIR OUT_DIR   (SRC_DIR = a checkout of the commit being measured)
set -euo pipefail
R=$1; D=$2; mkdir -p "$D"
zfix=/srv/opentallas-scratch/claude/q-vmwb/zfix; fix=/srv/opentallas-scratch/claude/q-attn-1015/fix/b_rl21_hxk8
stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; src=$stage/cp_minimal
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1)
python3 "$R/tools/qwen_attention_native/gen_pv_rate.py" --cp "$fix/cp_fix.sv" "$D/cp_w4.sv"
children=(qkd_astk_ep_cal_3 qkd_astk_ex qkd_astk_ep_cal_a qkd_astk_ep_cal_f qkd_astk_ep_cal_5 qkd_astk_ep_cal_0 qkd_astk_ep_cal_8 qkd_astk_ep_cal_e qkd_astk_ep_cal_2 qkd_astk_zn ot_qkh_head_native_r4_8)
sv=("$zfix/ctl/qkd_astk_ctl_tp8_cal_d.sv");for name in "${children[@]}";do sv+=("$stage/stubs/V$name/$name.sv");done
rm -rf "$D/cp"
"$vl" "${common[@]}" --top-module ot_qwen_tp8_attention_native_stack_w4_cp --prefix Vqattn_cp_w4 --mod-prefix Vqattn_cp_w4 --lib-create qattn_cp_w4 -GROW_RETURN_LAT=21 -GZ_STRIDE=16 --Mdir "$D/cp" "$src/ot_hdc_delay.sv" "$D/cp_w4.sv" "$src/ep_selector.sv" "$fix/ectl3/qkd_ectl3_epoch_direct_s_d.sv" "$R/rtl/qwen_sys/split_20261014/qkd_astk_native_er_service_w.sv" "${sv[@]}" > "$D/cp_build.log" 2>&1
python3 - "$R/rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_service_w16.sv" "$D" <<'PYGEN'
import sys
from pathlib import Path
svc,out=Path(sys.argv[1]),Path(sys.argv[2]);s=svc.read_text()
old='ot_qwen_tp8_attention_native_stack_w4_cp #(.QK_ISSUE_AGE(QK_ISSUE_AGE),.ROW_RETURN_LAT(ROW_RETURN_LAT),\n   .Z_STRIDE(Z_STRIDE)) u_stack('
assert s.count(old)==1;s=s.replace(old,'qattn_cp_w4 u_stack(')
old='ot_qkd_ahub_static_die_cal #(.Z_IN_STRIDE(Z_STRIDE),.Z_LEVEL_GAP(10),.ZW_RLY(0),.ZR_RLY(0),.RX_RLY(1),.RY_RLY(1)) u_hub('
assert s.count(old)==1;s=s.replace(old,'ot_qkd_ahub_static_die_cal_3 u_hub(')
old='ot_qwen_tp8_pv256_finalize_static_cal u_final('
assert s.count(old)==1;s=s.replace(old,'ot_qwen_tp8_pv256_finalize_static_cal_8 u_final(')
# drop the source stack_cp module (the library above replaces it)
i=s.index('// Common-phase stack entry');s=s[:i]
(out/'service.sv').write_text(s)
PYGEN
# the 16-chain slice (4 x 32x128 macros) as its own protected library (512 instances in the parent)
rm -rf "$D/slice"
"$vl" --cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module ot_qwen_tp8_pv16_slice --prefix Vqattn_pv16_slice --mod-prefix Vqattn_pv16_slice --lib-create qattn_pv16_slice --Mdir "$D/slice" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv" "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_fastfp.sv" "$R/rtl/hdc/ot_hdc_fpu.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v" > "$D/slice_build.log" 2>&1
sed -e 's/^module qattn_pv16_slice/module ot_qwen_tp8_pv16_slice/' "$D/slice/qattn_pv16_slice.sv" > "$D/slice/ot_qwen_tp8_pv16_slice.sv"
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_ectl3_epoch_direct_s_d.a|*/libqkd_astk_ctl_tp8_cal_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
[[ ${#libs[@]} == 30 ]]
libs+=("$fix/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$D/cp/libqattn_cp_w4.a" "$zfix/ctl/libqkd_astk_ctl_tp8_cal_d.a" "$D/slice/libqattn_pv16_slice.a")
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
fp=("$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_fastfp.sv" "$R/rtl/hdc/ot_hdc_fpu.sv")
for dm in ${DMUTS:-0 1 2}; do
rm -rf "$D/parent$dm"
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module tb_qwen_tp8_attention_native_service_w16 -GDMUT=$dm -GTRACE=1 --Mdir "$D/parent$dm" -LDFLAGS "$link" "$D/cp/qattn_cp_w4.sv" "$D/slice/ot_qwen_tp8_pv16_slice.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "${fp[@]}" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_vrow_capture.sv" "$D/service.sv" "$R/rtl/test/nearhbm/tb_qwen_tp8_attention_native_service_w16.sv" > "$D/parent${dm}_build.log" 2>&1 &
done
wait
for dm in ${DMUTS:-0 1 2}; do test -x "$D/parent$dm/Vtb_qwen_tp8_attention_native_service_w16"; done
sha256sum "$D"/cp/libqattn_cp_w4.a "$D"/parent*/Vtb_qwen_tp8_attention_native_service_w16 "$D/cp_w4.sv" "$D/service.sv" > "$D/artifacts.sha256"
echo BUILD_OK
