#!/bin/bash
# TOK-QW xdie_bound 2026-10-24: compute -> KV D2D exchange co-sim on the BOUND die masters with the CAL-AUTO regenerated
# link constants (physical/die_plan/qwen_compute/bind/bound_r8/regen/constants.json: XDIE_DIE_STAGES, D2D_TXDP_C,
# D2D_TXDP_K, D2D_KV_TX_LAT).  Harness = main's tb_xdie_qwen_exchange golden / landing checks (make_tb.py adds only the
# `XB_C_OVL compute-master swap).  usage (repo root): run_xdie_bound.sh OUTDIR [CONFIG ...]
#   compute master  qfd_d2d_static_ovl_sf7_obs1 PR 1  (bound_r8 glue.u_d2d_rom)  -- TXDP: compiled value applied by the bench
#                   (the bound top carries NONE: XB_C_TXDP_ASBOUND=1 config = the as-bound build)
#   KV master       qkd_d2d_static_sfm FEG 1 NL 2 NTX 3 SAFE_RC 1 SRAMV 2 TXDP 03030443 (bound_pv kv3_sys_c_part.u_d2d_kv)
#   seam            XDIE_DIE_STAGES 2,2,2,3,2,2/34,34,32,32,32,31,31 (bench xq_dly chains)
#   PHY pair        ot_qkvd_ucie_x64_phy_model (the model inside the bound ot_qkvd_ucie_x64_phy), LAT 5
#   stand-ins       compute native59 = qfd_native59_dv_service (bound: qfd_native59_dv_headprep_obs1), KV attention =
#                   qkd_kvs_attn_fl r17 + qkd_pv_fin_s (the bound KV die has no such tile: attention is distributed)
set -u
OUT=$1; shift
R=$(pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
X=tools/qwen_tokfunc/xdie_bound
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014; Q=rtl/qwen_split
B=$(python3 -c "import json;print(json.load(open('physical/die_plan/qwen_compute/bind/bound_r8/regen/constants.json'))['constants']['XDIE_DIE_STAGES']['value'])" 2>/dev/null)
[ -n "$B" ] || B='2,2,2,3,2,2/34,34,32,32,32,31,31'
OLD='2,2,2,3,2,2/11,11,9,9,9,9,9'      # the seam the bound calendar images were compiled for (K22 pair image)
LAW='--c-real 1 --k-real 3 --kv-codec 2 --attn-tx-shift 1 --status-delay 213'
G='-GC_REAL=1 -GK_REAL=4 -GK_NTX=3 -GPOS_P=255 -DXQ_K_SFM -DXB_C_OVL'
# name | expect | calendar flags | bench flags | mod
GS='-GC_REAL=1 -GK_REAL=4 -GK_NTX=3 -GPOS_P=255 -DXQ_K_SFM'   # source compute master qfd_d2d_static (+ bound KV master)
# name | expect | calendar flags | bench flags | mod   (bnd_* = bound compute master; src_* = source compute master qfd_d2d_static;
# om_* = bound compute master with its STATUS observer extension masked = DIAGNOSTIC source mod, not die RTL)
CONFIGS=(
 # F6: the bound compute master's STATUS kind15 v1 observer extension (DATA[511:304]) vs the bound KV master's legacy
 # status RX (ot_qwen_d2d_status_rx_sf: d[511:156] must be 0) -> KV status fault at the first STATUS landing
 "bnd_pair|FAIL|$LAW --stages $B|$G"
 "om_pair|PASS|$LAW --stages $B|$G|obsmask"
 "om_pair_t8192|PASS|$LAW --stages $B|$G -GPOS_P=8191|obsmask"
 "om_pair_l0|PASS|$LAW --layer L0 --stages $B|$G|obsmask"
 "om_mut_txdp_k_p1|FAIL|$LAW --stages $B --masters-txdp 8,3,1,10/68,4,3,3|$G|obsmask"
 "om_mut_seam_ks_rxv_p1|FAIL|$LAW --stages $B|$G|obsmask,seam:KS_RXV:+1"
 "om_mut_result_bit|FAIL|$LAW --stages $B|$G -GMUT=9|obsmask"
 "src_pair|PASS|$LAW --stages $B|$GS"
 "src_pair_t8192|PASS|$LAW --stages $B|$GS -GPOS_P=8191"
 "src_pair_l0|PASS|$LAW --layer L0 --stages $B|$GS"
 "src_pair_phy9|PASS|$LAW --phy 9 --stages $B|$GS"
 "bnd_asbound_c_txdp|BUILD_FAIL|$LAW --stages $B|$G -GXB_C_TXDP_ASBOUND=1"
 "src_asbound_kimage|FAIL|$LAW --stages $OLD|$GS|asbound_img"
 "src_mut_txdp_k_m1|FAIL|$LAW --stages $B --masters-txdp 8,3,1,10/66,4,3,3|$GS"
 "src_mut_txdp_k_p1|FAIL|$LAW --stages $B --masters-txdp 8,3,1,10/68,4,3,3|$GS"
 "src_mut_txdp_c_p1|FAIL|$LAW --stages $B --masters-txdp 9,3,1,10/67,4,3,3|$GS"
 "src_mut_seam_ks_rxv_p1|FAIL|$LAW --stages $B|$GS|seam:KS_RXV:+1"
 "src_mut_seam_sk_txp_p1|FAIL|$LAW --stages $B|$GS|seam:SK_TXP:+1"
 "src_mut_seam_cs_txs_p1|FAIL|$LAW --stages $B|$GS|seam:CS_TXS:+1"
 "src_mut_result_bit|FAIL|$LAW --stages $B|$GS -GMUT=9"
 "src_mut_status_done|FAIL|$LAW --stages $B|$GS -GMUT=8"
 "src_mut_phy_bit|FAIL|$LAW --stages $B|$GS -GMUT=2"
 "src_mut_kv_run_late|FAIL|$LAW --stages $B|$GS -GMUT=1"
)
SRC=("rtl/lib/ot_rst_pipe.sv" "$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
 "$S/qkd_native_attention_record.sv" "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_services.sv" "$Q/qfd_kvn_static_transport.sv"
 "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$Q/qfd_native59_dv_service.sv" "$Q/qfd_native59_q_export_control.sv" "$Q/qfd_native59_command_context.sv"
 "$Q/qfd_native59_static_service.sv" "$Q/qfd_native59_record_endpoint.sv" "rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$S/qkd_native_attention_programme.sv" "$S/qkd_native59_descriptor_producer.sv" "$S/qkd_native_attention_static_ctl.sv"
 "$S/qkd_native59_command_guard.sv" "$S/qkd_attn_cal_gen.sv" "$S/qkd_attn_service_root.sv" "$S/qkd_attn_result_face_s.sv"
 "$S/qkd_pv_fin_s.sv" "rtl/hdc/ot_hdc_fp32_add_lat.sv" "rtl/hdc/ot_hdc_fp32_mul_lat.sv" "rtl/hdc/ot_hdc_prefix.sv" "rtl/hdc/ot_hdc_fastfp.sv"
 "rtl/lib/ot_pin_land.sv" "rtl/lib/face_land/qkd_kvs_attn_fl_r17.sv" "rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_r17.sv"
 "$D/ot_qwen_d2d_safe_fo.sv" "$D/ot_qwen_d2d_sfm.sv"
 "physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v"
 "$D/ot_qwen_d2d_dies.sv" "rtl/test/qwen_split/xdie_kvs14c/qkd_kvs_attn_kvs14c.sv"
 # the bound compute master's closure (bound_carve + stage_closure of bound_r8 glue)
 "$D/ot_qwen_status_observers_v1.sv" "$D/ot_qwen_d2d_safe7.sv" "$D/ot_qwen_d2d_safe5.sv"
 "physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v"
 "$X/sram_p192_shim.sv")
mkdir -p "$OUT"
python3 $X/make_tb.py rtl/test/qwen_split/tb_xdie_qwen_exchange.sv "$OUT/tb_xdie_bound.sv" > /dev/null || exit 2
sha256sum "${SRC[@]}" rtl/test/qwen_split/tb_xdie_qwen_exchange.sv "$OUT/tb_xdie_bound.sv" tools/qwen_split/xdie_exchange_cal.py \
  tools/qwen_split/d2d_link_calendar.py physical/die_plan/qwen_compute/bind/bound_r8/regen/constants.json "$0" > "$OUT/source.sha256"
echo "bound seam B=$B" > "$OUT/params.txt"
want=("$@")
one() {
  local name=$1 exp=$2 calf=$3 gf="$4 ${XQ_G:-}" mod=${5:-} o=$OUT/$1
  mkdir -p "$o"
  python3 tools/qwen_split/xdie_exchange_cal.py --out "$o/cal" $calf > "$o/cal.log" 2>&1 || { echo "$name expect=$exp got=CAL_FAIL -> UNEXPECTED"; tail -3 "$o/cal.log"; return; }
  local src=("${SRC[@]}") m
  for m in ${mod//,/ }; do
  case "$m" in
   obsmask)       # DIAGNOSTIC: the compute STATUS TX without the observer extension (legacy DATA[511:156] = 0)
     sed 's/assign tx_payload={base_payload\[547:512\],held_obs,148.d0,base_payload\[155:0\]};/assign tx_payload=base_payload;   \/\/ xdie_bound obsmask DIAGNOSTIC/' \
       $D/ot_qwen_status_observers_v1.sv > "$o/ot_qwen_status_observers_v1_obsmask.sv"
     grep -q 'obsmask DIAGNOSTIC' "$o/ot_qwen_status_observers_v1_obsmask.sv" || { echo "$name got=MOD_FAIL -> UNEXPECTED"; return; }
     src=("${src[@]/$D\/ot_qwen_status_observers_v1.sv/$o/ot_qwen_status_observers_v1_obsmask.sv}");;
   asbound_img)   # calendars compiled for the OLD seam (what the bound dcal / sys_face images hold); seam + KV TXDP as bound
     python3 tools/qwen_split/xdie_exchange_cal.py --out "$o/cal_b" $LAW --stages $B >> "$o/cal.log" 2>&1 || { echo "$name got=CAL_FAIL -> UNEXPECTED"; return; }
     python3 - "$o/cal/xdie_params.svh" "$o/cal_b/xdie_params.svh" <<'PY'
import re, sys
a, b = open(sys.argv[1]).read(), open(sys.argv[2]).read()
for n in ['CS_TXS','CS_RXV','CS_RXP','CS_X3S','SC_TX','SC_X3','KS_RXV','KS_RXP','KS_TXS','KS_TXK','KS_TXB','SK_TXV','SK_TXP']:
    v = re.search(rf'localparam integer {n} = (\d+);', b).group(1)
    a = re.sub(rf'localparam integer {n} = \d+;', f'localparam integer {n} = {v};', a)
a = re.sub(r"localparam \[31:0\] P_TXDP_K = 32'h[0-9a-f]+;", "localparam [31:0] P_TXDP_K = 32'h03030443;", a)
open(sys.argv[1], 'w').write(a)
PY
     echo "asbound_img: OLD-seam calendars + bound seam + bound KV TXDP 03030443" >> "$o/cal.log";;
   seam:*)         # bench seam stage +1 vs the compiled calendar
     IFS=: read -r _ sn sd <<< "$m"
     python3 - "$o/cal/xdie_params.svh" "$sn" "$sd" <<'PY'
import re, sys
p, n, d = sys.argv[1], sys.argv[2], int(sys.argv[3])
a = open(p).read(); v = int(re.search(rf'localparam integer {n} = (\d+);', a).group(1))
open(p, 'w').write(re.sub(rf'localparam integer {n} = \d+;', f'localparam integer {n} = {v + d};', a)); print(n, v, '->', v + d)
PY
     ;;
  esac
  done
  grep -E "P_TXDP|KS_|SK_|CS_|SC_" "$o/cal/xdie_params.svh" | tr '\n' ' ' | sed 's/localparam //g' > "$o/params.txt"
  $V --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     -DOT_MEM_NO_INIT -I"$o/cal" --top-module tb_xdie_qwen_exchange $gf -GCALDIR="\"$o/cal\"" --Mdir "$o/obj" \
     "${src[@]}" "$OUT/tb_xdie_bound.sv" > "$o/build.log" 2>&1 || {
       if [ "$exp" = BUILD_FAIL ] && grep -q 'D2D_TXDP_NOT_COMPILED' "$o/build.log"; then
         echo "$name expect=$exp got=BUILD_FAIL -> OK"; grep -m2 'D2D_TXDP_NOT_COMPILED' "$o/build.log" | sed 's/^/    /'; cp "$o/build.log" "$o/run.log"
       else echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; fi
       rm -rf "$o/obj"; return; }
  "$o/obj/Vtb_xdie_qwen_exchange" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^XQ_PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)"
  echo "    $(cat $o/params.txt)"
  grep -E '^XQ_(E|CFG|PASS|FAIL|CAUSE|FIN)' "$o/run.log" | sed 's/^/    /'
  grep -m3 '^XQ_ERR' "$o/run.log" | sed 's/^/    /'
}
pids=()
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r name exp calf gf mod <<< "$c"
  if [ ${#want[@]} -gt 0 ] && ! printf '%s\n' "${want[@]}" | grep -qx "$name"; then continue; fi
  one "$name" "$exp" "$calf" "$gf" "$mod" > "$OUT/$name.summary" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
cat "$OUT"/*.summary | tee "$OUT/SUMMARY.txt"
! grep -q 'UNEXPECTED' "$OUT/SUMMARY.txt"
