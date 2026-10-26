#!/bin/bash
# Q-VMWB zfix: static ASTK CTL lib rebuilt from c8ce7c73f (ctl_lib.sh, b4 hier args), cp lib rebuilt against its wrapper
# (b_rl21_hxk8 recipe: real ECTL3 RL21/HXK8 lib + cp_fix.sv), parent relinked (fix_r3 service.sv, Codex min-parent).
set -euo pipefail
D=/srv/opentallas-scratch/claude/q-vmwb/zfix; fix=/srv/opentallas-scratch/claude/q-attn-1015/fix/b_rl21_hxk8
stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; src=$stage/cp_minimal
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1)
children=(qkd_astk_native_er_service_2 qkd_astk_ep_cal_3 qkd_astk_ex qkd_astk_ep_cal_a qkd_astk_ep_cal_f qkd_astk_ep_cal_5 qkd_astk_ep_cal_0 qkd_astk_ep_cal_8 qkd_astk_ep_cal_e qkd_astk_ep_cal_2 qkd_astk_zn ot_qkh_head_native_r4_8)
sv=("$D/ctl/qkd_astk_ctl_tp8_cal_d.sv");for name in "${children[@]}";do sv+=("$stage/stubs/V$name/$name.sv");done
rm -rf $D/cp
"$vl" "${common[@]}" --top-module ot_qwen_tp8_attention_native_stack_cp --prefix Vqattn_cp_fix --mod-prefix Vqattn_cp_fix --lib-create qattn_cp_fix -GROW_RETURN_LAT=21 -GZ_STRIDE=16 --Mdir "$D/cp" "$src/ot_hdc_delay.sv" "$fix/cp_fix.sv" "$src/ep_selector.sv" "$fix/ectl3/qkd_ectl3_epoch_direct_s_d.sv" "${sv[@]}" > "$D/cp_build.log" 2>&1
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_ectl3_epoch_direct_s_d.a|*/libqkd_astk_ctl_tp8_cal_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
[[ ${#libs[@]} == 30 ]]
libs+=("$fix/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$D/cp/libqattn_cp_fix.a" "$D/ctl/libqkd_astk_ctl_tp8_cal_d.a")
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
for dm in 0 1; do
rm -rf "$D/parent$dm"
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module tb_qwen_tp8_attention_native_service -GDMUT=$dm -GTRACE=1 --Mdir "$D/parent$dm" -LDFLAGS "$link" "$D/cp/qattn_cp_fix.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_c/ot_qwen_tp8_pv256_pair_c.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_b/ot_qwen_tp8_pv256_pair_b.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "$stage/qattn_minparent_pair.sv" "$stage/ot_qwen_tp8_vrow_static.sv" "$stage/ot_qwen_tp8_vrow_capture.sv" "$fix/service.sv" "$stage/tb_qwen_tp8_attention_native_service.sv" > "$D/parent${dm}_build.log" 2>&1
done
sha256sum $D/ctl/libqkd_astk_ctl_tp8_cal_d.a $D/cp/libqattn_cp_fix.a $D/parent0/Vtb_qwen_tp8_attention_native_service $D/parent1/Vtb_qwen_tp8_attention_native_service $D/src/rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv > $D/artifacts.sha256
echo BUILD_OK
