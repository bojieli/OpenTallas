#!/usr/bin/env bash
# S81-SERDES-RST-TREE (DIE-S81-85 2026-11-09): lock-step bench of ot_pdie_serdes_col RST_TREE=1 vs the released column
# (tb_s81_col_rst_tree), plus the two-die column link bench tb_s81_pdie_col under +define+OT_S81_SERDES_RST_TREE, plus the
# loopback latency bench tb_s81_col_rlat.
# usage: [RT_DEFS="+define+..."] run_serdes_rst_tree_bench.sh MODE OUTDIR
#   MODE: tree (PASS) | tree_ls (PASS, LOCKSAFE=1) | mut_rt2 / mut_nocomp (FAIL; *_ls with LOCKSAFE=1) | col | col_ref |
#         ref_col (PASS) | col_mut1 (FAIL) | rlat (PASS, prints lat_min / lat_max) | rlat_mut8 (FAIL with RT_EXPECT) |
#         vc_ls (PASS: RST_TREE=3 two leaf stages + RST_RT=1 retime, LOCKSAFE=1) | vc_mut_rt4 / vc_mut_short / vc_mut_nocomp (FAIL)
#   RT_TREE=2 uses +define+OT_S81_SERDES_RST_TREE2+OT_S81_SERDES_RST_RETIME (rlat of form vC).
#   RT_DEFS: extra defines, e.g. the vB combined form "+define+OT_S81_KP4_AM_FACE3+OT_S81_RCK_RELAY4+OT_S81_KP4_SYN_LOCAL
#            +OT_S81_RM_STAGED+OT_S81_RM_LOCAL4+OT_S81_RM_WFULL8" (RELAY4 needs LOCKSAFE=1: tree_ls / *_ls / rlat only).
#   RT_TREE=0 drops +define+OT_S81_SERDES_RST_TREE (rlat reference builds).
# Verilator 5.050 (fleet); never on localhost.
set -u
mode=${1:?mode}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link; M=$R/physical/asap7_memory_macros
VL=${VERILATOR:-verilator}
d=${RT_DEFS:-}; [ "${RT_TREE:-1}" = 1 ] && d="+define+OT_S81_SERDES_RST_TREE $d"
[ "${RT_TREE:-1}" = 2 ] && d="+define+OT_S81_SERDES_RST_TREE+OT_S81_SERDES_RST_TREE2+OT_S81_SERDES_RST_RETIME $d"
case $mode in
  tree) top=tb_s81_col_rst_tree; g="-GRT=1";; tree_ls) top=tb_s81_col_rst_tree; g="-GRT=1 -GLS=1";;
  mut_rt2) top=tb_s81_col_rst_tree; g="-GRT=2";; mut_nocomp) top=tb_s81_col_rst_tree; g="-GRT=1 -GNOCOMP=1";;
  mut_rt2_ls) top=tb_s81_col_rst_tree; g="-GRT=2 -GLS=1";; mut_nocomp_ls) top=tb_s81_col_rst_tree; g="-GRT=1 -GNOCOMP=1 -GLS=1";;
  col) top=tb_s81_pdie_col; g="-GMODE=0";; col_ref) top=tb_s81_pdie_col; g="-GMODE=1";; ref_col) top=tb_s81_pdie_col; g="-GMODE=2";;
  col_mut1) top=tb_s81_pdie_col; g="-GMODE=0 -GMUT=1";;
  rlat) top=tb_s81_col_rlat; g="";;
  vc_ls) top=tb_s81_col_rst_tree; g="-GRT=3 -GRTT=1 -GLS=1";;              # form vC: PASS
  vc_mut_rt4) top=tb_s81_col_rst_tree; g="-GRT=4 -GRTT=1 -GLS=1";;         # FAIL: encoder reset on the mid stage
  vc_mut_short) top=tb_s81_col_rst_tree; g="-GRT=3 -GRTT=1 -GLS=1 -GTXSHORT=1";;   # FAIL: retime edge not compensated
  vc_mut_nocomp) top=tb_s81_col_rst_tree; g="-GRT=3 -GRTT=1 -GLS=1 -GNOCOMP=1";;   # FAIL
  rlat_mut8) top=tb_s81_col_rlat; g="-GMUT=8";;
  *) echo "RST_TREE BAD_MODE $mode"; exit 2;; esac
[ -n "${RT_EXPECT:-}" ] && g="$g -GEXPECT_LAT=$RT_EXPECT"   # rlat modes: fixed latency required
$VL --version > "$out/verilator.version" 2>&1
$VL --binary --timing -j ${COL_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  $d --top-module $top $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" \
  "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" \
  "$L/ot_s81_kp4_dec.sv" "$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/native/ot_s81_kp4_dec_native_flat.sv" \
  "$L/lp/ot_s81_kp4_dec_native_flat_lp.sv" "$R/rtl/common/landed_parent/ot_pl_land.sv" "$L/col/ot_pdie_serdes_col.sv" \
  "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
  "$L/col/$top.sv" > "$out/build.log" 2>&1 || { echo "RST_TREE BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+${COL_SEED:-11} > "$out/run.log" 2>&1
grep -E '^(ERR|TX lock|RM:|RST_TREE|%Error)' "$out/run.log" | head -3
grep -E '^TB_S81_(COL_RST_TREE|PDIE_COL|COL_RLAT)' "$out/run.log" | tail -2
grep -qE '^TB_S81_(COL_RST_TREE|PDIE_COL|COL_RLAT) PASS$' "$out/run.log"
