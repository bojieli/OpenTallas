#!/bin/bash
# Q-ATTN-RATE: KV-die v1.4.3 composition bench binary = the 16-row/cycle service (build_w16.sh recipe) with
#  - ECTL3 rebuilt from source at HXK=$HXK (default 5, the qkd_ectl_*_h5 leaves of claude/qelem-ectl-h5-1705)
#  - every native r4 head behind the G3S2 stages (3 ingress G/T1/T2 + 2 score S1/S2: head_g3s2_wrap.sv, the CLOSED
#    qkh_head_gather_stage / qkh_head_tstage / qkh_head_sstage RTL)
# Usage: HXK=5 build_h5.sh SRC_DIR OUT_DIR W16_BUILD (W16_BUILD = a build_w16.sh output: its slice lib is reused)
set -euo pipefail
R=$1; D=$2; W=$3; HXK=${HXK:-5}; mkdir -p "$D"
zfix=/srv/opentallas-scratch/claude/q-vmwb/zfix; fix=/srv/opentallas-scratch/claude/q-attn-1015/fix/b_rl21_hxk8
stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; src=$stage/cp_minimal
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1)
mapfile -t ESRC < <(tr ' ' '\n' < /srv/opentallas-scratch/claude/q-attn-1015/b4/obj/Vqkd_ectl3_epoch_direct_s_d__hierMkArgs.f | grep -E '^(rtl|physical)/' | grep -v -e '^rtl/test/' -e 'ot_qwen_tp8_attention_native_service.sv$' | sed "s#^#$R/#")
rm -rf "$D/ectl3"
"$vl" "${common[@]}" --top-module qkd_ectl3_epoch_direct_s -GSTATIC_QK=1 -GQK_ISSUE_AGE=34 -GROW_RETURN_LAT=21 -GHXK=$HXK --prefix Vqkd_ectl3_epoch_direct_s_d --mod-prefix Vqkd_ectl3_epoch_direct_s_d --lib-create qkd_ectl3_epoch_direct_s_d --Mdir "$D/ectl3" "${ESRC[@]}" > "$D/ectl3_build.log" 2>&1
python3 "$R/tools/qwen_attention_native/gen_pv_rate.py" --cp "$fix/cp_fix.sv" "$D/cp_w4.sv"
python3 - "$D/cp_w4.sv" <<'PY'
import sys;p=sys.argv[1];s=open(p).read();a='   ot_qkh_head_native_r4_8 u_head(';assert s.count(a)==1;open(p,'w').write(s.replace(a,'   qattn_head_g3s2 u_head('))
PY
children=(qkd_astk_ep_cal_3 qkd_astk_ex qkd_astk_ep_cal_a qkd_astk_ep_cal_f qkd_astk_ep_cal_5 qkd_astk_ep_cal_0 qkd_astk_ep_cal_8 qkd_astk_ep_cal_e qkd_astk_ep_cal_2 qkd_astk_zn ot_qkh_head_native_r4_8)
sv=("$zfix/ctl/qkd_astk_ctl_tp8_cal_d.sv");for name in "${children[@]}";do sv+=("$stage/stubs/V$name/$name.sv");done
rm -rf "$D/cp"
"$vl" "${common[@]}" --top-module ot_qwen_tp8_attention_native_stack_w4_cp --prefix Vqattn_cp_w4 --mod-prefix Vqattn_cp_w4 --lib-create qattn_cp_w4 -GROW_RETURN_LAT=21 -GZ_STRIDE=16 --Mdir "$D/cp" "$src/ot_hdc_delay.sv" "$D/cp_w4.sv" "$src/ep_selector.sv" "$D/ectl3/qkd_ectl3_epoch_direct_s_d.sv" "$R/rtl/qwen_sys/split_20261014/qkd_astk_native_er_service_w.sv" "$R/tools/qwen_attention_native/rate_1015/head_g3s2_wrap.sv" "$R/rtl/qwen_sys/split_20261014/qkh_head_gather_stage.sv" "$R/rtl/qwen_sys/split_20261014/qkh_head_stages.sv" "${sv[@]}" > "$D/cp_build.log" 2>&1
cp "$W/service.sv" "$D/service.sv"
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_ectl3_epoch_direct_s_d.a|*/libqkd_astk_ctl_tp8_cal_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
libs+=("$D/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$D/cp/libqattn_cp_w4.a" "$zfix/ctl/libqkd_astk_ctl_tp8_cal_d.a" "$W/slice/libqattn_pv16_slice.a")
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
fp=("$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_fastfp.sv" "$R/rtl/hdc/ot_hdc_fpu.sv")
for dm in ${DMUTS:-0 2}; do
rm -rf "$D/parent$dm"
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module tb_qwen_tp8_attention_native_service_w16 -GDMUT=$dm -GTRACE=1 --Mdir "$D/parent$dm" -LDFLAGS "$link" "$D/cp/qattn_cp_w4.sv" "$W/slice/ot_qwen_tp8_pv16_slice.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "${fp[@]}" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_vrow_capture.sv" "$D/service.sv" "$R/rtl/test/nearhbm/tb_qwen_tp8_attention_native_service_w16.sv" > "$D/parent${dm}_build.log" 2>&1 &
done
wait
for dm in ${DMUTS:-0 2}; do test -x "$D/parent$dm/Vtb_qwen_tp8_attention_native_service_w16"; done
sha256sum "$D"/ectl3/libqkd_ectl3_epoch_direct_s_d.a "$D"/cp/libqattn_cp_w4.a "$D"/parent*/Vtb_qwen_tp8_attention_native_service_w16 "$D/cp_w4.sv" > "$D/artifacts.sha256"
echo BUILD_OK HXK=$HXK
