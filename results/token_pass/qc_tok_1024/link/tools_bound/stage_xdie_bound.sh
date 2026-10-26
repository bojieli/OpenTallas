#!/bin/bash
# TOK-FUNC-QW stage "xdie" (10-21): Qwen compute <-> KV D2D exchange co-sim, 35 decode layers bit-exact, 1 user, on the
# RTL-only SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050.
#
#   stage_xdie.sh RUNROOT [--die-netlist DIR]
#
# Bench = the existing QW-XDIE vehicle rtl/test/qwen_split/run_xdie_exchange.sh + tb_xdie_qwen_exchange.sv (486462c3f,
# in the assembly), cur_* family (C_REAL=1 K_REAL=4 -DXQ_K_SFM):
#   compute: qfd_d2d_static (PR 1, TXDP from the calendar) + qfd_native59_dv_service (MCTX / RX-epoch fix, NU 1 as the die binds)
#   KV:      qkd_d2d_static_sfm (GEN9 kit r7w_sfm2: NL 2 NTX 3 SAFE_RC 1 SRAMV 2 FEG 1) + qkd_kvs_attn_fl r17
#            (RETIRE_STATIC 1, STATUS_DELAY 213) + qkd_pv_fin_s;  cur_bound_image_sfm3 = same with the sfm3 successor master
# Seam = XQ_CUR 2,2,2,3,2,2 / 11,11,9,9,9,9,9 = the die stages the shared pair image was compiled for (image header
#   D2D_TXDP_C comment: g5r2b/g5r3 compute netlisted seam / K22 pair-image KV seam); the GEN9 d22bu as-built KV seam
#   13/9/11 is cur_kseam_d22bu_route_r (+2/exchange) and cur_kseam_d22bu_bound (TXDP 22: FAIL witness).
# ONE shared pair image: rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh (KV-PROG17: attn-tx-shift 1,
#   STATUS_DELAY 213, EMB_WIN 595).  The bench copy here (bench/run_xdie_exchange_img.sh, generated from the assembly's
#   script, nothing else changed) adds a calendar hook "img": after the law compile, xdie_image_cal.py replaces the four
#   segment-0 calendars + both TXDP words with the image's (and records law == image in cal/image_bind.json).
#   cur_bound_image (expect XQ_BOUND_EXPECT, default PASS here) / _t8192 / _sfm3 run on the image; cur_bound_image_tile_sd0
#   (image vs a tile without the STATUS tail) and cur_old_k22_image (the pre-PROG17 shift0/sd0 image = old cur_bound_image)
#   are FAIL witnesses, plus the existing cur_mut_* mutants.
# 4 users: NOT in this bench (native59 NU 1, one user per layer exchange); the OVL 4u pair is a separate stage.
#
# --die-netlist DIR (closure hook): not wired yet.  At closure the two D2D masters (u_c qfd_d2d_static, u_k
#   qkd_d2d_static_sfm*) and the KV tile u_kattn (qkd_kvs_attn_fl) are the GEN carves DIR/{qfd_d2d_static,qkd_d2d_static_sfm,
#   qkd_kvs_attn_fl}.v: add them to SRC_COMMON in front of the RTL files and drop the RTL copies (same module names);
#   grade = die-netlist.  Until then --die-netlist exits 2.
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
[ -n "$NET" ] && { echo "--die-netlist: hook documented in the header, not wired (no GEN carve yet)"; exit 2; }
SRC=$RUNROOT/src; S=$RUNROOT/xdie; FX=$S/fx; T=$S/tree; HERE=$(dirname "$(readlink -f "$0")")
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VERILATOR --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
[ -f "$FX/results/arch/token_path_20261009/qwen_rom.json" ] || { echo "missing fixtures $FX (physical phy model + macros_v2 .v, results/arch token_path + res_train decision)"; exit 2; }
rm -rf "$T" "$S/out" "$S/bench"; mkdir -p "$T/physical" "$S/bench"
for d in rtl tools configs; do cp -as "$SRC/$d" "$T/"; done
cp -as "$SRC/physical/." "$T/physical/" 2>/dev/null; cp -as "$FX/physical/." "$T/physical/"; cp -as "$FX/results" "$T/"
cp "$HERE/xdie_image_cal.py" "$S/bench/"
# RTL fix overlay (XDIE_OVERLAY=DIR, default RUNROOT/xdie/overlay if present): DIR/<repo path> replaces the assembly file
# in the tree; listed in result.json "overlay" (fix branch claude/tokfunc-qw-xdie-fix-1021 until the assembly carries it)
OVL=${XDIE_OVERLAY:-$S/overlay}; : > "$S/overlay.txt"
if [ -d "$OVL" ]; then (cd "$OVL" && find . -type f | sed 's#^\./##') | while read -r f; do
  rm -f "$T/$f"; cp "$OVL/$f" "$T/$f"; echo "$f $(sha256sum < "$OVL/$f" | cut -c1-16)" >> "$S/overlay.txt"; done; fi
# --- bench copy with the image hook (anchors asserted; any drift in the assembly's script fails here, not silently)
python3 - "$T/rtl/test/qwen_split/run_xdie_exchange.sh" "$S/bench/run_xdie_exchange_img.sh" <<'PY' || exit 3
import sys
s = open(sys.argv[1]).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, ('anchor', old[:80], s.count(old))
    s = s.replace(old, new)
rep(' "cur_bound_image|${XQ_BOUND_EXPECT:-FAIL}|--c-real 1 --k-real 3 --kv-codec 2 --stages $CUR|$CUR_G"\n',
    ' "cur_old_k22_image|FAIL|--c-real 1 --k-real 3 --kv-codec 2 --stages $CUR|$CUR_G"\n'
    ' # TOK-FUNC-QW xdie: the ONE shared pair image (XQ_IMAGE, KV-PROG17 ew595_r16) bound into both dies\' calendars + TXDP\n'
    ' "cur_bound_image|${XQ_BOUND_EXPECT:-PASS}|$CUR_LAW --stages $CUR|$CUR_G|img"\n'
    ' "cur_bound_image_t8192|PASS|$CUR_LAW --stages $CUR|$CUR_G -GPOS_P=8191|img"\n'
    ' "cur_bound_image_sfm3|PASS|$CUR_LAW --stages $CUR|$CUR_G|img_sfm3"\n'
    ' "cur_bound_image_mut_result_bit|FAIL|$CUR_LAW --stages $CUR|$CUR_G -GMUT=9|img"\n')
rep(' "cur_bound_image_tile_sd0|${XQ_BOUND_EXPECT:-FAIL}|--c-real 1 --k-real 3 --kv-codec 2 --stages $CUR|$CUR_G -GK_SD=0"\n',
    ' "cur_bound_image_tile_sd0|FAIL|$CUR_LAW --stages $CUR|$CUR_G -GK_SD=0|img"\n')
rep('  # the die masters take TXDP from the compiler (xdie_params.svh P_TXDP_C / P_TXDP_K; QXF-LINK F4): no source patching\n',
    '  local srcs=() f\n'
    '  case "$mod" in img|img_sfm3)\n'
    '    python3 "$XQ_IMGTOOL" --image "$XQ_IMAGE" --cal "$o/cal" >> "$o/cal.log" 2>&1 || { echo "$name expect=$exp got=CAL_FAIL -> UNEXPECTED"; tail -3 "$o/cal.log"; return; }\n'
    '    grep IMAGE_BIND "$o/cal.log" | sed "s/^/    /";;\n'
    '  esac\n'
    '  for f in "${SRC_COMMON[@]}"; do\n'
    '    if [ "$mod" = img_sfm3 ] && [ "$f" = rtl/test/qwen_split/tb_xdie_qwen_exchange.sv ]; then\n'
    '      sed "s/qkd_d2d_static_sfm #(/qkd_d2d_static_sfm3 #(/" "$f" > "$o/tb_sfm3.sv"; grep -q "qkd_d2d_static_sfm3 #(" "$o/tb_sfm3.sv" || { echo "$name expect=$exp got=MOD_FAIL -> UNEXPECTED"; return; }\n'
    '      srcs+=("$o/tb_sfm3.sv" "$D/ot_qwen_d2d_sfm3.sv")\n'
    '    else srcs+=("$f"); fi\n'
    '  done\n'
    '  # the die masters take TXDP from the compiler (xdie_params.svh P_TXDP_C / P_TXDP_K; QXF-LINK F4): no source patching\n')
rep('     "${SRC_COMMON[@]}" "$kattn" "$D/ot_qwen_d2d_dies.sv" > "$o/build.log"', '     "${srcs[@]}" "$kattn" "$D/ot_qwen_d2d_dies.sv" > "$o/build.log"')
rep('--masters-txdp 9,3,1,10/22,4,3,3', '--masters-txdp 9,3,1,10/${XQ_TXDP_K:-22,4,3,3}')
open(sys.argv[2], 'w').write(s)
PY
chmod +x "$S/bench/run_xdie_exchange_img.sh"
# QC-TOK 10-24: the bound pair image (regen_constants xdie_pair_image recipe) and the bound seam
export XQ_IMAGE=${XQ_IMAGE:?XQ_IMAGE} XQ_CUR=${XQ_CUR:?XQ_CUR} XQ_IMGTOOL=$S/bench/xdie_image_cal.py
export XQ_BOUND_EXPECT=${XQ_BOUND_EXPECT:-PASS} JOBS=${JOBS:-2}
CFGS=(cur_pair cur_bound_image cur_bound_image_t8192 cur_bound_image_sfm3 cur_pair_t8192 cur_pair_phy9 cur_pair_l0
      cur_shift_only_sd0 cur_kseam_d22bu_route_r
      cur_bound_image_tile_sd0 cur_bound_image_mut_result_bit cur_old_k22_image cur_no_status_tail cur_c_rx_codec1
      cur_kseam_d22bu_bound cur_mut_no_base cur_mut_txdp_c_off1 cur_mut_status_done cur_mut_result_bit cur_mut_phy_bit
      cur_mut_kseam_rx_torn cur_mut_kv_run_late)
cd "$T" || exit 3
# law == image check on the plain cur_pair compile (record; the run itself uses the law compile, cur_bound_image the image)
mkdir -p "$S/out"
python3 tools/qwen_split/xdie_exchange_cal.py --out "$S/out/law_check" --c-real 1 --k-real 3 --kv-codec 2 --attn-tx-shift 1 \
  --status-delay 213 --stages $XQ_CUR > "$S/out/law_check.log" 2>&1 \
  && python3 "$XQ_IMGTOOL" --image "$XQ_IMAGE" --cal "$S/out/law_check" --check-only >> "$S/out/law_check.log" 2>&1
bash "$S/bench/run_xdie_exchange_img.sh" "$S/out" "${CFGS[@]}" > "$S/run.log" 2>&1; RC=$?
echo "RUN_RC $RC" >> "$S/run.log"
python3 "$HERE/stage_xdie.collect.py" "$RUNROOT" "$RC"
