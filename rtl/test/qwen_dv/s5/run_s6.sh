#!/usr/bin/env bash
# QW-S5-LP 10-21: benches of the slice2 W/E master with CLOSED children bound (tools/qwen_dv/gen_slice6_lp_spec.py), run on
# the FLEET from the repository root, Verilator 5.050 (the closure daemon's version).
#   lp <M>  landed parent rtl/qwen_dv/s5/s6/lp/<SPEC>_lp vs its lagref (the s6 flat with every cross-region reader pin
#           delayed E+1), lp.py MUT M: 0 must print LP_LOCKSTEP PASS; 1 (landing 0 bypassed), 2 (landing 0 read K+1),
#           4 (u_ctl reset run one stage long) must print LP_LOCKSTEP FAIL.  SPEC=qfd_dv_s6 (D4/E2) | qfd_dv_s6b (D8/E4)
#   lint    Verilator lint of qfd_dv_s6_flat and of qfd_dv_s6_lp under the kit defines (OT_S5_HARD)
#   bash rtl/test/qwen_dv/s5/run_s6.sh OUTDIR lp|lint [M]
set -u
OUT=$1; KIND=$2; M=${3:-0}; mkdir -p "$OUT"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
SP=${SPEC:-qfd_dv_s6}; LPD=rtl/qwen_dv/s5/s6/lp
# below-leaf RTL (run_s5.sh COMMON without the s5 leaves / old VM, SRAM models = the non-fatal copies)
COMMON="rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
 rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv
 rtl/test/qwen_dv/s5/sram_models_nofatal.sv
 rtl/qwen_dv/qfd_dv_heads.sv rtl/lib/ot_rst_pipe.sv
 rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv rtl/qwen_dv/qfd_dv_su_lane.sv rtl/hdc/ot_hdc_vstream_lane_t.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv
 rtl/qwen_dv/qfd_dv_slice_tload.sv rtl/qwen_dv/qfd_dv_table_rom_loader.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_station_math_g.sv
 rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv
 rtl/common/landed_parent/ot_pl_land_physical.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv rtl/common/landed_parent/ot_pl_land_split.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v"
# the child modules (gen_slice6_lp_spec.CHILD_SOURCES) + the flat parent
CHILD=$(python3 -c 'import sys; sys.path.insert(0,"tools/qwen_dv"); import gen_slice6_lp_spec as g; print(" ".join(g.CHILD_SOURCES))')
VF="--binary --timing -O2 -j ${VJOBS:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 +define+OT_STATION_REGIONAL +define+OT_S5_HARD"
case $KIND in
  lp)
    "$V" $VF -GMUT=$M --top-module tb_${SP}_lp $COMMON $CHILD rtl/qwen_dv/s5/s6/qfd_dv_s6_flat.sv \
      $LPD/${SP}_flat_lagref.sv $LPD/${SP}_lp.sv $LPD/tb_${SP}_lp.sv -Mdir "$OUT/obj_lp$M" > "$OUT/build_lp$M.log" 2>&1 \
      || { echo "BUILD FAIL"; grep -m30 '%Error' "$OUT/build_lp$M.log"; exit 1; }
    "$OUT/obj_lp$M/Vtb_${SP}_lp" > "$OUT/lp$M.log" 2>&1
    r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/lp$M.log" | head -1)
    grep -m6 -i "mismatch\|LAND_FAULT" "$OUT/lp$M.log"
    echo "LP $SP M=$M: ${r:-NO_RESULT}";;
  lint)
    for T in qfd_dv_s6_flat ${SP}_lp; do
      "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT +define+OT_STATION_REGIONAL +define+OT_S5_HARD \
        --top-module $T $COMMON $CHILD rtl/qwen_dv/s5/s6/qfd_dv_s6_flat.sv $LPD/${SP}_lp.sv > "$OUT/lint_$T.log" 2>&1
      e=$(grep -c '%Error' "$OUT/lint_$T.log"); echo "LINT $T: errors=$e"; grep -m20 '%Error' "$OUT/lint_$T.log"
    done;;
  *) echo "unknown kind $KIND"; exit 2;;
esac
