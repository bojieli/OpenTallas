#!/usr/bin/env bash
# S81-SERDES 10-19: every bench of the landed SerDes column (FLEET only, via ot-run; Verilator 5.050 as the closure daemon):
#   lp/   lp.py lockstep flat vs landed (MUT 0 PASS, MUT 1-4 FAIL) + region audit (+ unland mutant audit FAIL)
#   link_m<MODE>/  tb_s81_pdie_col two-die link, die B 300 ppm slow (pma_rck != clk: CDC children exercised), MUT 0:
#          MODE 0 column<->column, 1 column A -> reference ot_pdie_serdes B, 2 reference A -> column B; each must PASS.
#   bash rtl/dsrom_sys/s81_link/col/lp/run_col_lp_all.sh OUTDIR
set -u
cd "$(dirname "$0")/../../../../.."
OUT=${1:-col_lp_out}; mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --version > "$OUT/verilator.version" 2>&1
I=rtl/dsrom_sys/s81_link
( SIM=verilator VERILATOR=$VL VL_JOBS=4 VL_EXTRA="-I$I" bash $I/col/lp/ot_pdie_serdes_col_lp_bench.sh "$OUT/lp" > "$OUT/lp.log" 2>&1 ) &
LS="$I/col/tb_s81_pdie_col.sv $I/col/ot_pdie_serdes_col_lpw.sv $I/col/lp/ot_pdie_serdes_col_lp.sv $I/col/ot_s81_col_leaf.sv \
 $I/col/ot_s81_pma_models.sv $I/ot_s81_kp4_common.sv $I/ot_s81_kp4_bm.sv $I/ot_s81_kp4_dsyn.sv $I/ot_s81_kp4_ddly.sv \
 $I/ot_s81_kp4_dchn.sv $I/ot_s81_kp4_dout.sv $I/ot_s81_kp4_enc.sv $I/ot_s81_kp4_dec.sv $I/ot_pdie_serdes.sv \
 rtl/common/landed_parent/ot_pl_land.sv physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
for m in 0 1 2; do
  ( d="$OUT/link_m$m"; mkdir -p "$d"
    $VL --binary -j 4 -I$I -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 --top-module tb_s81_pdie_col \
      -GMODE=$m -GMUT=0 $LS -Mdir "$d/obj" > "$d/build.log" 2>&1 && "$d/obj/Vtb_s81_pdie_col" > "$d/run.log" 2>&1
    echo "LINK MODE $m: $(grep -o 'TB_S81_PDIE_COL [A-Z]*' "$d/run.log" 2>/dev/null | tail -1)" ) > "$OUT/link_m$m.res" &
done
wait
cat "$OUT/lp.log" "$OUT"/link_m*.res
rc=0; grep -q "BENCH_EXIT 0" "$OUT/lp.log" || rc=1
for m in 0 1 2; do grep -q "TB_S81_PDIE_COL PASS" "$OUT/link_m$m.res" || rc=1; done
echo "COL_LP_ALL_EXIT $rc"; exit $rc
