#!/bin/bash
set -euo pipefail
me=/srv/opentallas-scratch/claude/q-attn-1015/fix; stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015; out=$me/b_rl21
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 - <<'PY'
from pathlib import Path
me=Path('/srv/opentallas-scratch/claude/q-attn-1015/fix');s=(me/'svc_fix_dbg.sv').read_text();old='ot_qwen_tp8_attention_native_stack_cp_c u_stack(';assert s.count(old)==1;(me/'b_rl21/service_dbg.sv').write_text(s.replace(old,'qattn_cp_fix u_stack('))
PY
libs=();while IFS= read -r file;do case "$file" in */libot_qwen_tp8_attention_native_stack_cp_c.a|*/libqkd_ectl3_epoch_direct_s_d.a) ;; *)libs+=("$file");;esac;done < <(find "$stage/stubs" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
libs+=("$out/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$out/cp/libqattn_cp_fix.a"); link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
rm -rf $out/parentdbg
"$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+QATTN_SVC_DBG --top-module tb_qwen_tp8_attention_native_service --Mdir "$out/parentdbg" -LDFLAGS "$link" "$out/cp/qattn_cp_fix.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_c/ot_qwen_tp8_pv256_pair_c.sv" "$stage/stubs/Vot_qwen_tp8_pv256_pair_b/ot_qwen_tp8_pv256_pair_b.sv" "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" "$stage/qattn_minparent_pair.sv" "$stage/ot_qwen_tp8_vrow_static.sv" "$stage/ot_qwen_tp8_vrow_capture.sv" "$out/service_dbg.sv" "$stage/tb_qwen_tp8_attention_native_service.sv" > "$out/parentdbg_build.log" 2>&1
$out/parentdbg/Vtb_qwen_tp8_attention_native_service +VEC=$stage/vectors/full8192 +CTX=8192 +MODE=steady +CAL=124e124e124e05aa07bc076c06af032705aa03200352 > $me/runs/dbg_full.log 2>&1 || true
grep -c SVCDBG $me/runs/dbg_full.log
