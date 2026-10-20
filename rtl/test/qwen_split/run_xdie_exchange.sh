#!/bin/bash
# TOKEN-XDIE-QWEN 2026-10-18: Qwen compute <-> KV D2D exchange co-sim (tb_xdie_qwen_exchange.sv), Verilator 5.050.
# usage (repository root, on the fleet via ot-run): run_xdie_exchange.sh OUTDIR [CONFIG ...]   (default: every config)
# Each config: compile its calendar (tools/qwen_split/xdie_exchange_cal.py), build, run; one line per config:
#   <name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED
# Exit 0 only when every config met its expectation.  Logs: OUTDIR/<name>/{cal/,build.log,run.log}.
set -u
OUT=$1; shift
R=$(pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014; Q=rtl/qwen_split
NET_C='2,0,2,2,0,2'            # dv2f14bn as netlisted: tx_slot / rx_payload / kv_x3_slot / x3 landed E 2, rx_v + tx_v direct
NET_K='9,11,9,8,9,6,11'        # kvs14c as netlisted: srx 9, rx_payload 11, att_tx slot 9 / kind 8 / beat 9, tx_v 6, tx_payload 11
# every bundle at its netlisted member maximum (what the die plan must build; F5 / F6): compute tx_record (tx_v + payload)
# is direct in dv2f14bn -> SC_TX 0 (QXF-LINK 10-18; run_r3 used 2 -> TXDP C [8,3,1,9]; the compiler's die-run table and
# LAYERBENCH-QWEN compiled_L1 give 0 -> C [6,3,1,9])
PLAN=${XQ_PLAN:-'2,2,2,2,0,2/11,11,9,9,9,11,11'}
# Q-XDIE-GEN 10-18: XQ_PLAN = the NETLISTED seam of the current die GENs (lane cycles per record bundle, E + 1 for a landed
# forwarded lane: record_bundle_audit.json / BUNDLE_EQ); XQ_G = extra bench -G flags for every config (e.g. -GK_NTX=3);
# XQ_TXDP_OFF1 = the off-by-one compute TXDP mutant for that plan; XQ_GEN_TXDP = the TXDP the die GENs BIND (pair_gen_txdp)
GEN_TXDP=${XQ_GEN_TXDP:-'6,3,1,9/23,4,3,3'}
PLAN_R3='2,2,2,2,2,2/11,11,9,9,9,11,11'
ZERO='0,0,0,0,0,0/0,0,0,0,0,0,0'
# QXF-SEAMK 10-18 (F6): kvs14c after the generator's bundle pads (tools/qwen_kv_die/kv_bundle_eq.py: srx +2, kind +1, tx_v +5)
# and the OT_KV_ATTN_AT_D2D placement (kvs_attn beside the D2D end: rx 1/1, tx slot 0/0/0, tx 0/0, pin geometry of kvs14c)
BEQ_K='11,11,9,9,9,11,11'
AT_D2D_K='1,1,0,0,0,0,0'   # kvs_attn W of the HOST root, N face at the D2D end's bottom (OT_KV_ATTN_D2D_TOP 0)
OLDTXDP='3,3,1,4/3,4,3,3'      # the r4..r9 masters' hard-wired PR TXDP (component-bench codecs)
PAIR_TXDP_OFF1=${XQ_TXDP_OFF1:-'7,3,1,9/23,4,3,3'}   # QXF-PAIR mutant: compute CMD/Q port TXDP one edge over the compiled C [6,3,1,9]
# name | expect (PASS | FAIL | BUILD_FAIL) | calendar flags | bench -G flags [| source mod: face4 = vendored kvs_attn face MUT 4]
CONFIGS=(
 "vc|PASS|--c-real 1 --k-real 0 --stages $PLAN|-GC_REAL=1 -GK_REAL=0"
 "vk|PASS|--c-real 0 --k-real 1 --stages $PLAN|-GC_REAL=0 -GK_REAL=1"
 "full|PASS|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1"
 "full_phy9|PASS|--c-real 1 --k-real 1 --phy 9 --stages $PLAN|-GC_REAL=1 -GK_REAL=1"
 "full_abut|PASS|--c-real 1 --k-real 1 --stages $ZERO|-GC_REAL=1 -GK_REAL=1"
 "full_r3stages|PASS|--c-real 1 --k-real 1 --stages $PLAN_R3|-GC_REAL=1 -GK_REAL=1"
 "full_l0|PASS|--c-real 1 --k-real 1 --layer L0 --stages $PLAN|-GC_REAL=1 -GK_REAL=1"
 "vc_phy9|PASS|--c-real 1 --k-real 0 --phy 9 --stages $PLAN|-GC_REAL=1 -GK_REAL=0"
 "vk_phy9|PASS|--c-real 0 --k-real 1 --phy 9 --stages $PLAN|-GC_REAL=0 -GK_REAL=1"
 "full_gap1|FAIL|--c-real 1 --k-real 1 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GQGAP=1"
 "f1_n59_legacy_window|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=6"
 "f2_kv_status_legacy|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=7"
 "f2_vk_status_legacy|FAIL|--c-real 0 --k-real 1 --stages $PLAN|-GC_REAL=0 -GK_REAL=1 -GMUT=7"
 "mut5_kv_status_zero|FAIL|--c-real 1 --k-real 0 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GMUT=5"
 "f4_masters_stale_txdp|FAIL|--c-real 1 --k-real 1 --stages $PLAN --masters-txdp $OLDTXDP|-GC_REAL=1 -GK_REAL=1"
 "f4_masters_uncompiled|BUILD_FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GXQ_TXDP_UNSET=1"
 "f7_l0_priced_window|FAIL|--c-real 1 --k-real 1 --layer L0 --no-extend --stages $PLAN|-GC_REAL=1 -GK_REAL=1"
 "face_asbuilt|FAIL|--c-real 0 --k-real 2 --stages $PLAN|-GC_REAL=0 -GK_REAL=2"
 "netlist_c|FAIL|--c-real 1 --k-real 0 --stages $NET_C/0,0,0,0,0,0,0|-GC_REAL=1 -GK_REAL=0"
 "netlist_k|FAIL|--c-real 0 --k-real 1 --stages 0,0,0,0,0,0/$NET_K|-GC_REAL=0 -GK_REAL=1"
 "netlist_k_beq|PASS|--c-real 0 --k-real 1 --stages 0,0,0,0,0,0/$BEQ_K|-GC_REAL=0 -GK_REAL=1"
 "vk_attn_d2d|PASS|--c-real 0 --k-real 1 --stages 2,2,2,2,2,2/$AT_D2D_K|-GC_REAL=0 -GK_REAL=1"
 "mut_attn_d2d_torn|FAIL|--c-real 0 --k-real 1 --stages 2,2,2,2,2,2/0,1,0,0,0,0,0|-GC_REAL=0 -GK_REAL=1"
 "mut1_kv_run_late|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=1"
 "mut2_phy_bit|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=2"
 "mut3_result_word|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=3"
 "mut4_qslot_late|FAIL|--c-real 1 --k-real 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GMUT=4"
 # QXF-FACE 10-18 (F3): as-built kvs_attn + REAL qkd_pv_fin_s, face / pvfin on the max(P0, P1, R) law, T = 256 and 8192
 "fin_t256|PASS|--c-real 0 --k-real 3 --stages $PLAN|-GC_REAL=0 -GK_REAL=3 -GPOS_P=255"
 "fin_t8192|PASS|--c-real 0 --k-real 3 --stages $PLAN|-GC_REAL=0 -GK_REAL=3 -GPOS_P=8191"
 "fin_t256_face_noR|FAIL|--c-real 0 --k-real 3 --stages $PLAN|-GC_REAL=0 -GK_REAL=3 -GPOS_P=255|face4"
 "fin_t8192_face_noR|FAIL|--c-real 0 --k-real 3 --stages $PLAN|-GC_REAL=0 -GK_REAL=3 -GPOS_P=8191|face4"
 "fin_t256_pvfin_noR|FAIL|--c-real 0 --k-real 3 --stages $PLAN|-GC_REAL=0 -GK_REAL=3 -GPOS_P=255 -GFIN_MUT=3"
 # QXF-PAIR 10-18: the PAIRED co-sim -- compute native59 real (C_REAL=1) + KV as-built kvs_attn + real pvfin (K_REAL=3),
 # compute seam = one landed age per bundle (QXF-SEAMC lp_fix: C.rx_record 2, C.tx_record 0), KV seam = padded 11/9/11 (QXF-SEAMK)
 "pair|PASS|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_t8192|PASS|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=8191"
 "pair_phy9|PASS|--c-real 1 --k-real 3 --phy 9 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_l0|PASS|--c-real 1 --k-real 3 --layer L0 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_l0_phy9|PASS|--c-real 1 --k-real 3 --layer L0 --phy 9 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_gen_txdp|${XQ_GEN_TXDP_EXPECT:-PASS}|--c-real 1 --k-real 3 --stages $PLAN --masters-txdp $GEN_TXDP|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_mut_txdp_c_off1|FAIL|--c-real 1 --k-real 3 --stages $PLAN --masters-txdp $PAIR_TXDP_OFF1|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255"
 "pair_mut_kseam_rx_torn|FAIL|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255 -GK_TEAR=1"
 "pair_mut_kseam_tx_torn|FAIL|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255 -GK_TEAR=2"
 "pair_mut_status_done|FAIL|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255 -GMUT=8"
 "pair_mut_result_bit|FAIL|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255 -GMUT=9"
 "pair_mut_phy_bit|FAIL|--c-real 1 --k-real 3 --stages $PLAN|-GC_REAL=1 -GK_REAL=3 -GPOS_P=255 -GMUT=2"
)
SRC_COMMON=("rtl/lib/ot_rst_pipe.sv" "$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
 "$S/qkd_native_attention_record.sv" "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_services.sv" "$Q/qfd_kvn_static_transport.sv"
 "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$Q/qfd_native59_dv_service.sv" "$Q/qfd_native59_q_export_control.sv" "$Q/qfd_native59_command_context.sv"
 "$Q/qfd_native59_static_service.sv" "$Q/qfd_native59_record_endpoint.sv" "rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$S/qkd_native_attention_programme.sv" "$S/qkd_native59_descriptor_producer.sv" "$S/qkd_native_attention_static_ctl.sv"
 "$S/qkd_native59_command_guard.sv" "$S/qkd_attn_cal_gen.sv" "$S/qkd_attn_service_root.sv" "$S/qkd_attn_result_face_s.sv"
 "$S/qkd_pv_fin_s.sv" "rtl/hdc/ot_hdc_fp32_add_lat.sv" "rtl/hdc/ot_hdc_fp32_mul_lat.sv" "rtl/hdc/ot_hdc_prefix.sv" "rtl/hdc/ot_hdc_fastfp.sv"
 "rtl/test/qwen_split/tb_xdie_qwen_exchange.sv")
KATTN=rtl/test/qwen_split/xdie_kvs14c/qkd_kvs_attn_kvs14c.sv
mkdir -p "$OUT"
sha256sum "${SRC_COMMON[@]}" "$KATTN" "$D/ot_qwen_d2d_dies.sv" tools/qwen_split/xdie_exchange_cal.py tools/qwen_split/d2d_link_calendar.py "$0" > "$OUT/source.sha256"
want=("$@")
one() {
  local name=$1 exp=$2 calf=$3 gf="$4 ${XQ_G:-}" mod=${5:-} o=$OUT/$1 kattn=$KATTN
  mkdir -p "$o"
  if [ "$mod" = face4 ]; then   # QXF-FACE mutant: the vendored kvs_attn with its stream face at MUT 4 (R left out)
    grep -c 'qkd_attn_result_face_s #(.NF(10), .RESULT_RELAY(0), .F_DLY(1), .MUT(0))' "$KATTN" | grep -qx 1 || { echo "$name expect=$exp got=MOD_FAIL -> UNEXPECTED"; return; }
    sed 's/qkd_attn_result_face_s #(.NF(10), .RESULT_RELAY(0), .F_DLY(1), .MUT(0))/qkd_attn_result_face_s #(.NF(10), .RESULT_RELAY(0), .F_DLY(1), .MUT(4))/' "$KATTN" > "$o/qkd_kvs_attn_face4.sv"
    kattn="$o/qkd_kvs_attn_face4.sv"
  fi
  python3 tools/qwen_split/xdie_exchange_cal.py --out "$o/cal" $calf > "$o/cal.log" 2>&1 || { echo "$name expect=$exp got=CAL_FAIL -> UNEXPECTED"; tail -3 "$o/cal.log"; return; }   # QXF-FACE: a run that never simulated is no FAIL witness
  # the die masters take TXDP from the compiler (xdie_params.svh P_TXDP_C / P_TXDP_K; QXF-LINK F4): no source patching
  $V --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     -DOT_MEM_NO_INIT -I"$o/cal" --top-module tb_xdie_qwen_exchange $gf -GCALDIR="\"$o/cal\"" --Mdir "$o/obj" \
     "${SRC_COMMON[@]}" "$kattn" "$D/ot_qwen_d2d_dies.sv" > "$o/build.log" 2>&1 || {
       if [ "$exp" = BUILD_FAIL ] && grep -q 'D2D_TXDP_NOT_COMPILED' "$o/build.log"; then
         echo "$name expect=$exp got=BUILD_FAIL -> OK"; grep -m2 'D2D_TXDP_NOT_COMPILED' "$o/build.log" | sed 's/^/    /'; cp "$o/build.log" "$o/run.log"
       else echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; fi
       rm -rf "$o/obj"; return; }
  "$o/obj/Vtb_xdie_qwen_exchange" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^XQ_PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)"
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
