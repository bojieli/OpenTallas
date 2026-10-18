#!/bin/bash
# KVJ-B2 2026-10-17: regenerate the three build_w16.sh inputs that lived only on ot-epyc1tb (terminated 2026-10-16,
# not in the handrun harvest nor the AGIdock archive):
#   $ROOT/fix/b_rl21_hxk8   = minparent_1015/fix_r3/build_fix.sh with ROWLAT=21 HXK=8: cp_fix.sv + ECTL3 library
#   $ROOT/zfix/ctl          = results/arch/qwen_attention_native_calendar_1015/ctl_lib.sh: static ASTK CTL library
#   $ROOT/zfix/vec/<name>   = tools/qwen_tp8_attention_native.py vectors (zfix naming: full<T>, seed 1, kind normal)
# The b4 __hierMkArgs.f files both recipes read are gone with the host; they were the b4 hier-block argument lists,
# i.e. the source list of tools/qwen_attention_native/build.sh (minus rtl/test and the service) plus the block's
# parameters. Those are reproduced here: ECTL3 as build_fix.sh states them; the CTL block "_d" is the
# ot_qwen_tp8_attention_native_stack(_cal) u_ctl binding (STATIC_SCHEDULE 1, Z_STRIDE 16; LMAX/Z_START_AGE are
# unused in the cal variant). Port headers of both new wrappers are checked against the pinned minparent stubs.
# Sources come from SRC_DIR (a checkout of the commit being measured; it carries the zfix CTL and HXK ECTL3).
# Usage: regen_epyc1_deps.sh SRC_DIR ROOT [VEC_CTX...]   (default VEC_CTX: 1000 8192)
set -euo pipefail
R=$(realpath "$1"); ROOT=$(realpath -m "$2"); shift 2; if [[ $# -gt 0 ]]; then ctxs=("$@"); else ctxs=(1000 8192); fi
stage=${STAGE:-/srv/opentallas-scratch/codex/q-attn-minparent-1015}; src=$stage/cp_minimal
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
common=(--cc --build --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 32 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1)
fix=$ROOT/fix/b_rl21_hxk8; zfix=$ROOT/zfix; mkdir -p "$fix" "$zfix/vec"
(cd "$stage/stubs" && sha256sum -c --quiet "$stage/b4-artifacts.sha256")
mapfile -t ESRC < <(python3 - "$R/tools/qwen_attention_native/build.sh" <<'PY'
import re,sys
s=open(sys.argv[1]).read();m=re.search(r'^SRC="([^"]*)"',s,re.M)
for p in m.group(1).split():
    if not p.startswith('rtl/test/') and not p.endswith('ot_qwen_tp8_attention_native_service.sv'):print(p)
PY
)
(cd "$R" && ls "${ESRC[@]}" >/dev/null); printf '%s\n' "${ESRC[@]}" > "$ROOT/b4_hier_sources.txt"
cd "$R"
# fix/b_rl21_hxk8 (build_fix.sh ROWLAT=21 HXK=8: ECTL3 + cp_fix.sv; build_w16 uses only these two)
rm -rf "$fix/ectl3"
"$vl" "${common[@]}" --top-module qkd_ectl3_epoch_direct_s -GSTATIC_QK=1 -GQK_ISSUE_AGE=34 -GROW_RETURN_LAT=21 -GHXK=8 --prefix Vqkd_ectl3_epoch_direct_s_d --mod-prefix Vqkd_ectl3_epoch_direct_s_d --lib-create qkd_ectl3_epoch_direct_s_d --Mdir "$fix/ectl3" "${ESRC[@]}" > "$fix/ectl3_build.log" 2>&1 &
sed -e 's/qattn_ctl_debug u_ctl(/qkd_astk_ctl_tp8_cal_d u_ctl(/' -e "s/ROW_RETURN_LAT!=22/ROW_RETURN_LAT!=21/" "$src/cp_minimal.sv" > "$fix/cp_fix.sv"
grep -q 'qkd_astk_ctl_tp8_cal_d u_ctl(' "$fix/cp_fix.sv"
# zfix/ctl (ctl_lib.sh: static ASTK CTL library from source, Z sums by block index)
rm -rf "$zfix/ctl"
"$vl" "${common[@]}" --top-module qkd_astk_ctl_tp8_cal -GSTATIC_SCHEDULE=1 -GLMAX_START_AGE=0 -GZ_START_AGE=0 -GZ_STRIDE=16 --prefix Vqkd_astk_ctl_tp8_cal_d --mod-prefix Vqkd_astk_ctl_tp8_cal_d --lib-create qkd_astk_ctl_tp8_cal_d --Mdir "$zfix/ctl" "${ESRC[@]}" > "$zfix/ctl_build.log" 2>&1 &
for T in "${ctxs[@]}"; do python3 "$R/tools/qwen_tp8_attention_native.py" vectors --ctx "$T" --seed 1 --kind normal --out "$zfix/vec/full$T" > "$zfix/vec_full$T.log" 2>&1 & done
wait
hdr(){ sed -n '/^module/,/);/p' "$1" | tr -d ' \t,' | sort; }   # port set (Verilator orders lib ports differently)
for p in "$fix/ectl3/qkd_ectl3_epoch_direct_s_d.sv:Vqkd_ectl3_epoch_direct_s_d/qkd_ectl3_epoch_direct_s_d.sv" "$zfix/ctl/qkd_astk_ctl_tp8_cal_d.sv:Vqkd_astk_ctl_tp8_cal_d/qkd_astk_ctl_tp8_cal_d.sv"; do
  diff <(hdr "${p%%:*}") <(hdr "$stage/stubs/${p#*:}") > /dev/null || { echo "PORT HEADER MISMATCH ${p%%:*}"; exit 1; }
done
for T in "${ctxs[@]}"; do test -s "$zfix/vec/full$T/gold.hex"; done
sha256sum "$fix/cp_fix.sv" "$fix/ectl3/libqkd_ectl3_epoch_direct_s_d.a" "$fix/ectl3/qkd_ectl3_epoch_direct_s_d.sv" "$zfix/ctl/libqkd_astk_ctl_tp8_cal_d.a" "$zfix/ctl/qkd_astk_ctl_tp8_cal_d.sv" "$zfix"/vec/*/*.hex "$zfix"/vec/*/meta.json > "$ROOT/regen.sha256"
echo REGEN_OK
