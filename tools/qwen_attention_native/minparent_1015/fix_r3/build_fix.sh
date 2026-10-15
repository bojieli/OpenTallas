#!/bin/bash
# Q-ATTN r3 fix build: ROW_RETURN_LAT = K_EXT + 5 (= 21 at K_EXT 16), the measured native QK round trip
# (generator rq_valid -> RQD 2 relays -> face -> K_EXT boundary -> 3 response pin stages = K_EXT+5 edges;
# tools/qwen_kv_die/static_qk_calendar.py already derives row_latency+5). Production composition, no debug defines:
#  - qkd_ectl3_epoch_direct_s_d rebuilt from real source (b4 file list, src3 = 182417f9b) at ROW_RETURN_LAT=$ROWLAT
#  - stack_cp rebuilt from Codex cp_minimal with the REAL b4 ctl library (not ctl_debug), b4 EP/ER/EX/ZN/head libraries
#  - parent = Codex b5b min-parent with the stack_cp library swapped; SERVICE= selects the service source.
set -euo pipefail
stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; src=$stage/cp_minimal
me=/srv/opentallas-scratch/claude/q-attn-1015/fix; R=${SRCDIR:-/srv/opentallas-scratch/claude/q-attn-1015/src3}
ROWLAT=${ROWLAT:-21}; out=${OUT:-$me/b_rl$ROWLAT}; SERVICE=${SERVICE:-$me/ot_qwen_tp8_attention_native_service.sv}
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1)
(cd "$stage/stubs" && sha256sum -c "$stage/b4-artifacts.sha256") > "$out/b4_artifacts_check.log"
mapfile -t ESRC < <(tr ' ' '\n' < /srv/opentallas-scratch/claude/q-attn-1015/b4/obj/Vqkd_ectl3_epoch_direct_s_d__hierMkArgs.f | grep -E '^(rtl|physical)/' | grep -v -e '^rtl/test/' -e 'ot_qwen_tp8_attention_native_service.sv$' | sed "s#^#$R/#")
"$vl" "${common[@]}" --top-module qkd_ectl3_epoch_direct_s -GSTATIC_QK=1 -GQK_ISSUE_AGE=34 -GROW_RETURN_LAT=$ROWLAT -GHXK=${HXK:-0} --prefix Vqkd_ectl3_epoch_direct_s_d --mod-prefix Vqkd_ectl3_epoch_direct_s_d --lib-create qkd_ectl3_epoch_direct_s_d --Mdir "$out/ectl3" "${ESRC[@]}" > "$out/ectl3_build.log" 2>&1
sed -e 's/qattn_ctl_debug u_ctl(/qkd_astk_ctl_tp8_cal_d u_ctl(/' -e "s/ROW_RETURN_LAT!=22/ROW_RETURN_LAT!=$ROWLAT/" "$src/cp_minimal.sv" > "$out/cp_fix.sv"
grep -q 'qkd_astk_ctl_tp8_cal_d u_ctl(' "$out/cp_fix.sv"
children=(qkd_astk_ctl_tp8_cal_d qkd_astk_native_er_service_2 qkd_astk_ep_cal_3 qkd_astk_ex qkd_astk_ep_cal_a qkd_astk_ep_cal_f qkd_astk_ep_cal_5 qkd_astk_ep_cal_0 qkd_astk_ep_cal_8 qkd_astk_ep_cal_e qkd_astk_ep_cal_2 qkd_astk_zn ot_qkh_head_native_r4_8)
sv=();for name in "${children[@]}";do sv+=("$stage/stubs/V$name/$name.sv");done
"$vl" "${common[@]}" --top-module ot_qwen_tp8_attention_native_stack_cp --prefix Vqattn_cp_fix --mod-prefix Vqattn_cp_fix --lib-create qattn_cp_fix -GROW_RETURN_LAT=$ROWLAT -GZ_STRIDE=16 --Mdir "$out/cp" "$src/ot_hdc_delay.sv" "$out/cp_fix.sv" "$src/ep_selector.sv" "$out/ectl3/qkd_ectl3_epoch_direct_s_d.sv" "${sv[@]}" > "$out/cp_build.log" 2>&1
python3 - "$SERVICE" "$out" <<'PYGEN'
from pathlib import Path
import sys
svc,out=Path(sys.argv[1]),Path(sys.argv[2]);s=svc.read_text();old='ot_qwen_tp8_attention_native_stack_cp_c u_stack(';assert s.count(old)==1;s=s.replace(old,'qattn_cp_fix u_stack(');(out/'service.sv').write_text(s)
PYGEN
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_ectl3_epoch_direct_s_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
[[ ${#libs[@]} == 31 ]]; libs+=("$out/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$out/cp/libqattn_cp_fix.a")
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
for dm in 0 1; do
rm -rf "$out/parent$dm"
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module tb_qwen_tp8_attention_native_service -GDMUT=$dm -GTRACE=1 --Mdir "$out/parent$dm" -LDFLAGS "$link" "$out/cp/qattn_cp_fix.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_c/ot_qwen_tp8_pv256_pair_c.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_b/ot_qwen_tp8_pv256_pair_b.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "$stage/qattn_minparent_pair.sv" "$stage/ot_qwen_tp8_vrow_static.sv" "$stage/ot_qwen_tp8_vrow_capture.sv" "$out/service.sv" "$stage/tb_qwen_tp8_attention_native_service.sv" > "$out/parent${dm}_build.log" 2>&1
done
sha256sum "$out"/ectl3/libqkd_ectl3_epoch_direct_s_d.a "$out"/cp/libqattn_cp_fix.a "$out"/parent0/Vtb_qwen_tp8_attention_native_service "$out"/parent1/Vtb_qwen_tp8_attention_native_service "$SERVICE" "$out/cp_fix.sv" > "$out/artifacts.sha256"
echo BUILD_OK
