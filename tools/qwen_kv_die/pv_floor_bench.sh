#!/bin/bash
# KV-BIND8 10-20: PV pair END FLOOR bench (fixes KV_STATIC_PARAMS ATTN_CALENDAR PVFIN_PAIR_SKEW).
# Builds tb_qkd_pvw_die_t (the trunked pair qkd_pvw_die_t, golden bit-exact per column, static column ages) with the pair
# control ot_qwen_tp8_pv_wide_ctl_tbf (via the bench shim) at FLOOR=1 and FLOOR=0, runs PAIR 0 and PAIR 1 at contexts
# covering every skew class (T <= 128: empty pair 1 = skew 32; T mod 256 in 1..128: skew 16; else 0) and checks:
#   FLOOR=1  every run PASS (bit-exact, 32 columns, ages, no fault) and out_age(PAIR 1) == out_age(PAIR 0) at every T
#   FLOOR=0  every run PASS and out_age(PAIR 0) - out_age(PAIR 1) == the shipping skew 32/16/0 (the check sees the skew)
# usage: pv_floor_bench.sh OUT [CTXS]   (repo root; Verilator 5.050 = the closure daemon's)
# Prints PV_FLOOR PASS|FAIL; exit 0 only on PASS.
set -u
O=$1; CTXS=${2:-"1 64 128 129 200 256 257 300 384 385 512 1000 4097 8192"}; RL=${RL:-19}
mkdir -p "$O"; VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
rc=0
skew() { local T=$1; if [ $T -le 128 ]; then echo 32; else
  a=$(( ((T + 255) >> 8) )); b=$(( ((T - 128 + 255) >> 8) )); echo $(( 16 * (a - b) )); fi; }
# KV-FLOOR2 10-20: FLOORS (default "1 0") and CTL_MUT (bench mutant witness: +define+OT_CTL_MUT=n, expect PV_FLOOR FAIL)
MUTDEF=; [ -n "${CTL_MUT:-}" ] && MUTDEF="+define+OT_CTL_MUT=$CTL_MUT"
for F in ${FLOORS:-1 0}; do
  $VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs ${JOBS:-16} \
   --hierarchical --top-module tb_qkd_pvw_die_t -GRL=$RL +define+OT_END_FLOOR=$F $MUTDEF --Mdir "$O/obj_f$F" -Irtl/test/nearhbm \
   tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv \
   rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv rtl/lib/ot_rst_relay_bounded32.sv rtl/test/kv_bind8_1020/ot_qwen_tp8_pv_wide_ctl_t_floorshim.sv \
   rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
   physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv \
   rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv rtl/test/nearhbm/tb_qkd_pvw_die_t.sv \
   > "$O/build_f$F.log" 2>&1 || { echo "PV_FLOOR FAIL build FLOOR=$F"; tail -5 "$O/build_f$F.log"; exit 1; }
  # PAIR is a top parameter: rebuild per pair would double the build; the tb takes -GPAIR at build time, so build twice
  $VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs ${JOBS:-16} \
   --hierarchical --top-module tb_qkd_pvw_die_t -GRL=$RL -GPAIR=1 +define+OT_END_FLOOR=$F $MUTDEF --Mdir "$O/obj_f${F}_p1" -Irtl/test/nearhbm \
   tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv \
   rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv rtl/lib/ot_rst_relay_bounded32.sv rtl/test/kv_bind8_1020/ot_qwen_tp8_pv_wide_ctl_t_floorshim.sv \
   rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
   physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv \
   rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv rtl/test/nearhbm/tb_qkd_pvw_die_t.sv \
   > "$O/build_f${F}_p1.log" 2>&1 || { echo "PV_FLOOR FAIL build FLOOR=$F PAIR=1"; tail -5 "$O/build_f${F}_p1.log"; exit 1; }
  for T in $CTXS; do
    a0=; a1=
    for P in 0 1; do
      V="$O/vec_${T}_p$P"
      [ -f "$V/gold.hex" ] || python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair $P --seed $T --out "$V" >/dev/null \
        || { echo "PV_FLOOR FAIL T=$T pair=$P golden generation"; rc=1; continue; }
      B="$O/obj_f$F/Vtb_qkd_pvw_die_t"; [ $P = 1 ] && B="$O/obj_f${F}_p1/Vtb_qkd_pvw_die_t"
      line=$("$B" +VEC="$V" +CTX=$T | grep -E "^PV_PAIR_T" | tail -1)
      echo "FLOOR=$F $line"
      case "$line" in "PV_PAIR_T PASS"*) ;; *) rc=1;; esac
      age=$(echo "$line" | sed -n 's/.* out_age=\([0-9]*\).*/\1/p')
      [ $P = 0 ] && a0=$age || a1=$age
    done
    want=0; [ $F = 0 ] && want=$(skew $T)
    if [ -z "$a0" ] || [ -z "$a1" ] || [ $((a0 - a1)) != $want ]; then
      echo "PV_FLOOR SKEW FAIL FLOOR=$F T=$T out_age p0=$a0 p1=$a1 want p0-p1=$want"; rc=1
    else echo "PV_FLOOR SKEW ok FLOOR=$F T=$T p0=$a0 p1=$a1 p0-p1=$want"; fi
  done
done
[ $rc = 0 ] && echo "PV_FLOOR PASS (FLOOR=1 skew 0 at every context, bit-exact both pairs; FLOOR=0 shows the shipping skew)" || echo "PV_FLOOR FAIL"
exit $rc
