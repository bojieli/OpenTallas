#!/bin/bash
# Q-ATTN r3: ECTL observer build. As dbg_ep, plus the native QK engine qkd_ectl3_epoch_direct_s_d compiled from its real
# source (STATIC_QK=1/QK_ISSUE_AGE=34/ROW_RETURN_LAT=22) with QATTN_ECTL_DBG fault-term + age trace displays.
set -euo pipefail
stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; src=$stage/cp_minimal
me=/srv/opentallas-scratch/claude/q-attn-1015/dbg_ectl; out=$me/build; R=/srv/opentallas-scratch/claude/q-attn-1015/src3
ECTLP=${ECTLP:-$me/ectl_parts_dbg.sv}; ROWLAT=${ROWLAT:-22}
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 +define+QATTN_ECTL_DBG)
SRC=$(sed -n '/^SRC="/,/"$/p' $R/tools/qwen_attention_native/build.sh | tr -d '"' | sed 's/^SRC=//' | tr '\n' ' ')
EPSRC=(); for f in $SRC; do case $f in rtl/test/*|rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_service.sv) ;; rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv) EPSRC+=("$ECTLP");; *) EPSRC+=("$R/$f");; esac; done
[[ -f $out/ctl/libqattn_ctl_debug.a ]] || "$vl" "${common[@]}" --top-module qkd_astk_ctl_tp8_cal --prefix Vqattn_ctl_debug --mod-prefix Vqattn_ctl_debug --lib-create qattn_ctl_debug -GSTATIC_SCHEDULE=1 -GZ_STRIDE=16 +define+KVD_AKDBG --Mdir "$out/ctl" "$src/ctl_debug.sv" > "$out/ctl_build.log" 2>&1
children=(qkd_astk_native_er_service_2 qkd_astk_ex qkd_astk_zn ot_qkh_head_native_r4_8)
sv=();for name in "${children[@]}";do sv+=("$stage/stubs/V$name/$name.sv");done
sed "s/ROW_RETURN_LAT(22)/ROW_RETURN_LAT($ROWLAT)/" $me/ectl3_d_src.sv > $out/ectl3_d_src.sv
cpmin=$out/cp_minimal.sv; sed "s/ROW_RETURN_LAT!=22/ROW_RETURN_LAT!=$ROWLAT/" $src/cp_minimal.sv > $cpmin
"$vl" "${common[@]}" --top-module ot_qwen_tp8_attention_native_stack_cp --prefix Vqattn_cp_debug --mod-prefix Vqattn_cp_debug --lib-create qattn_cp_debug -GROW_RETURN_LAT=$ROWLAT -GZ_STRIDE=16 +define+QATTN_NATIVE_DBG +define+KVD_AKDBG --Mdir "$out/cp" "$src/ot_hdc_delay.sv" "$cpmin" "$me/ep_selector_dbg.sv" "$out/ctl/qattn_ctl_debug.sv" "$out/ectl3_d_src.sv" "${sv[@]}" "${EPSRC[@]}" > "$out/cp_build.log" 2>&1
python3 - "$stage" "$out" <<'PYGEN'
from pathlib import Path
import sys
stage,out=map(Path,sys.argv[1:]);s=(stage/'ot_qwen_tp8_attention_native_service.sv').read_text();old='ot_qwen_tp8_attention_native_stack_cp_c u_stack(';assert s.count(old)==1;s=s.replace(old,'qattn_cp_debug u_stack(');(out/'service.sv').write_text(s)
PYGEN
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_astk_ctl_tp8_cal_d.a|*/libqkd_astk_ep_cal_*.a|*/libqkd_ectl3_epoch_direct_s_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
libs+=("$out/ctl/libqattn_ctl_debug.a" "$out/cp/libqattn_cp_debug.a")
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 --top-module tb_qwen_tp8_attention_native_service --Mdir "$out/parent" -LDFLAGS "$link" "$out/cp/qattn_cp_debug.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_c/ot_qwen_tp8_pv256_pair_c.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_b/ot_qwen_tp8_pv256_pair_b.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "$stage/qattn_minparent_pair.sv" "$stage/ot_qwen_tp8_vrow_static.sv" "$stage/ot_qwen_tp8_vrow_capture.sv" "$out/service.sv" "$src/tb_prefix.sv" > "$out/parent_build.log" 2>&1
"$out/parent/Vtb_qwen_tp8_attention_native_service" +VEC=$stage/vectors/full8192 +CTX=8192 +MODE=steady > "$me/prefix.log" 2>&1 || true
grep -E "ECTLFAULT|RINGFAULT|FIRST_FAULT|DIAGNOSTIC" "$me/prefix.log" | head -40
