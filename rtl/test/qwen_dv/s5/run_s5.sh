#!/usr/bin/env bash
# QW-SLICE6 10-19: benches of the hardened one-level slice re-cut (run on the FLEET from the repository root, Verilator 5.050).
#   eq <M>  lockstep qfd_dv_slice2 (SU_TLS 1, SU_LT 1, HD_W130 1, MU_NU 4, PRIVATE_CALR 1; regional station PIN 0 =
#           +define+OT_STATION_REGIONAL, the stnrgc source) vs qfd_dv_s5_flat0 at offset 0, four stimulus modes
#           (random / +quiet / +hronly / +legal).  M = 0 must print S5_EQ PASS; M = d10 (SETID unincremented),
#           loff (lane offset twice), lrly (lane answers one relay stage short) must print S5_EQ FAIL.
#   b2 [M]  dv_bench2 f j k q m n o (B2=...) on FACE 3 (qfd_dv_s5_flat0: programme benches vs the golden); M as eq
#   lp <M>  landed parent vs lagref lockstep (SPEC=qfd_dv_s5|qfd_dv_s5b), lp.py MUT M;  audit: lp.py audits + unland mutants
#   lint    Verilator lint of qfd_dv_s5_flat (the HARDENED composition, closed lane head safe2 RTL)
#   bash rtl/test/qwen_dv/s5/run_s5.sh OUTDIR eq|b2|lint [M]
set -u
OUT=$1; KIND=$2; M=${3:-0}; mkdir -p "$OUT"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
COMMON="rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
 rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv
 rtl/test/full_sm_service/sram_models.sv rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/test/qwen_dv/safe_storage/sram_model.sv
 rtl/qwen_dv/qfd_dv_heads.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/lib/ot_rst_pipe.sv
 rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv rtl/qwen_dv/qfd_dv_su_lane.sv rtl/hdc/ot_hdc_vstream_lane_t.sv
 rtl/hdc/ot_hdc_vstream_sfu_t.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv
 rtl/qwen_dv/qfd_dv_slice_tload.sv rtl/qwen_dv/qfd_dv_table_rom_loader.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 rtl/qwen_dv/qfd_dv_redstn2_regional.sv rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_station_math_g.sv
 rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv
 rtl/common/landed_parent/ot_pl_land_physical.sv
 rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_vm.sv"
VF="--binary --timing -O2 -j ${VJOBS:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 +define+OT_STATION_REGIONAL"
case $KIND in
  eq)
    D=""; G=""
    case $M in 0) ;; d10) G="-GDMUT=10";; d11) G="-GDMUT=11";; d12) G="-GDMUT=12";; d9) G="-GDMUT=9";; loff) D="+define+OT_S5_LOFF_MUT";;
      lrly) D="+define+OT_S5_LRLY_MUT";; red) D="+define+OT_S5_RED_MUT";; sc) D="+define+OT_S5_SC_MUT";;
      xh) D="+define+OT_S5_XH_MUT";; btab) D="+define+OT_S5_BTAB_MUT";; *) echo "unknown M $M"; exit 2;; esac
    # random stimulus collides SRAM read/write by design: the bench links non-fatal copies of the three model files
    CE=$(echo $COMMON | tr ' ' '\n' | grep -v -e full_sm_service/sram_models.sv -e hbm_rf_visibility/scale_sram_model.sv -e safe_storage/sram_model.sv | tr '\n' ' ')
    "$V" $VF $D $G --top-module tb_qfd_dv_s5_flat0 $CE rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/s5/qfd_dv_s5_flat0.sv \
      rtl/test/qwen_dv/s5/tb_qfd_dv_s5_flat0.sv -Mdir "$OUT/obj_eq$M" > "$OUT/build_eq$M.log" 2>&1 || { echo "BUILD FAIL"; tail -30 "$OUT/build_eq$M.log"; }
    rs=""
    for mode in rand quiet hronly legal; do
      pa=""; [ $mode != rand ] && pa="+$mode"
      "$OUT/obj_eq$M/Vtb_qfd_dv_s5_flat0" $pa > "$OUT/eq${M}_$mode.log" 2>&1
      r=$(grep -o 'S5_EQ [A-Z]*' "$OUT/eq${M}_$mode.log" | head -1); rs="$rs $mode:${r#S5_EQ }"
      grep -m4 S5_MISMATCH "$OUT/eq${M}_$mode.log"; grep -h "S5_EQ\|S5_FAULT" "$OUT/eq${M}_$mode.log"
    done
    if ! echo "$rs" | grep -q -v ':PASS' <<< "$(echo $rs | tr ' ' '\n')"; then :; fi
    if [ "$(echo $rs | tr ' ' '\n' | grep -c ':PASS$')" = 4 ]; then echo "EQ M=$M: S5_EQ PASS ($rs)";
    elif echo "$rs" | grep -q ':FAIL'; then echo "EQ M=$M: S5_EQ FAIL ($rs)"; else echo "EQ M=$M: NO_RESULT ($rs)"; fi;;
  b2)
    D=""; case $M in 0) ;; loff) D="+define+OT_S5_LOFF_MUT";; lrly) D="+define+OT_S5_LRLY_MUT";; red) D="+define+OT_S5_RED_MUT";;
      sc) D="+define+OT_S5_SC_MUT";; xh) D="+define+OT_S5_XH_MUT";; btab) D="+define+OT_S5_BTAB_MUT";; esac
    MU=""; case $M in d*) MU="--mut ${M#d}";; esac
    python3 rtl/test/qwen_dv/dv_bench2.py ${B2:-f j k q m n o} $MU --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=3 $D" --work "$OUT/b2";;
  lp)
    # landed parent (lp.py) vs its lagref (the flat parent with every cross-region reader pin delayed E+1), lp.py MUT M
    # (0 PASS; 1 landing bypassed, 2 landing read K+1, 4 mut_child reset run long: FAIL).  SPEC=qfd_dv_s5 | qfd_dv_s5b
    SP=${SPEC:-qfd_dv_s5}; LPD=rtl/qwen_dv/s5/lp
    "$V" $VF +define+OT_S5_HARD -Wno-WIDTHCONCAT -GMUT=$M --top-module tb_${SP}_lp $COMMON rtl/qwen_dv/qfd_dv_head_safe1.sv \
      physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v rtl/qwen_dv/s5/qfd_dv_s5_flat.sv \
      $LPD/${SP}_flat_lagref.sv $LPD/${SP}_lp.sv $LPD/tb_${SP}_lp.sv -Mdir "$OUT/obj_lp$M" > "$OUT/build_lp$M.log" 2>&1 \
      || { echo "BUILD FAIL"; grep -m20 '%Error' "$OUT/build_lp$M.log"; }
    "$OUT/obj_lp$M/Vtb_${SP}_lp" > "$OUT/lp$M.log" 2>&1
    grep -m4 LP_MISMATCH "$OUT/lp$M.log"; r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/lp$M.log" | head -1); echo "LP $SP MUT=$M: ${r:-NO_RESULT}";;
  audit)
    for SP in qfd_dv_s5 qfd_dv_s5b; do
      python3 tools/landed_parent/lp.py audit tools/landed_parent/specs/$SP.json > "$OUT/audit_$SP.log" 2>&1 && echo "AUDIT $SP PASS" || echo "AUDIT $SP FAIL"
      python3 tools/landed_parent/lp.py audit tools/landed_parent/specs/$SP.json --rtl "$OUT/unland_$SP.sv" --make-unland \
        > "$OUT/audit_unland_$SP.log" 2>&1 && echo "AUDIT-UNLAND $SP PASSED (should FAIL)" || echo "AUDIT-UNLAND $SP FAIL (expected)"
    done;;
  lint)
    "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD +define+OT_STATION_REGIONAL --top-module qfd_dv_s5_flat \
      $COMMON rtl/qwen_dv/qfd_dv_head_safe1.sv physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v rtl/qwen_dv/s5/qfd_dv_s5_flat.sv > "$OUT/lint.log" 2>&1; echo "LINT rc=$?"; grep -m20 "%Error" "$OUT/lint.log";;
esac
