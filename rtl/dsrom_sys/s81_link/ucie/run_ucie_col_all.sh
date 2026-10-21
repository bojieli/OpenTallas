#!/usr/bin/env bash
# HBM-UCIE8 10-20: every bench of the landed HBM host UCIe column (FLEET only, via ot-run; Verilator 5.050 as the closure
# daemon pins):
#   audit     lp.py region audit of the generated column (PASS; 0 landings: the only rck -> clk crossings are CDC children)
#   lp_m<M>/  lp.py lockstep flat ot_pdie_ucie_col_flat vs landed ot_pdie_ucie_col: MUT 0 PASS, MUT 4 (live-flag reset run
#             40 stages long) FAIL
#   link_m<MODE>/  tb_pdie_ucie_col two-die link, die B 300 ppm slow: MODE 0 column<->column, 1 column A -> reference
#             ot_pdie_ucie B, 2 reference A -> column B; each must PASS
#   linkmut_<M>/   MODE 0 with mutant M (1 SRAM read address +1, 2 write valid stuck 0, 3 status flag stuck 0): each must FAIL
#   bash rtl/dsrom_sys/s81_link/ucie/run_ucie_col_all.sh OUTDIR
set -u
cd "$(dirname "$0")/../../../.."
OUT=${1:-ucie_col_out}; mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --version > "$OUT/verilator.version" 2>&1
I=rtl/dsrom_sys/s81_link
U=$I/ucie
CS="$U/ot_ucie_col_leaf.sv $U/ot_ucie_pma_models.sv $I/col/ot_s81_col_leaf.sv $I/ot_pdie_serdes.sv rtl/common/landed_parent/ot_pl_land.sv \
 $I/col/ot_s81_rate_match_sr.sv physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v $U/lp/ot_pdie_ucie_col.sv"
VLF="--binary -j 4 -I$I -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1"
python3 tools/landed_parent/lp.py audit tools/landed_parent/specs/ot_pdie_ucie_col.json > "$OUT/audit.log" 2>&1 \
  && echo "AUDIT PASS" > "$OUT/audit.res" || echo "AUDIT FAIL" > "$OUT/audit.res"
for m in 0 4; do
  ( d="$OUT/lp_m$m"; mkdir -p "$d"
    $VL $VLF --top-module tb_ot_pdie_ucie_col -GMUT=$m $U/ot_pdie_ucie_col_flat.sv $CS $U/lp/tb_ot_pdie_ucie_col.sv -Mdir "$d/obj" \
      > "$d/build.log" 2>&1 && "$d/obj/Vtb_ot_pdie_ucie_col" > "$d/run.log" 2>&1
    echo "LP MUT $m: $(grep -o 'LP_LOCKSTEP [A-Z]*' "$d/run.log" 2>/dev/null | tail -1)" ) > "$OUT/lp_m$m.res" &
done
LS="$U/tb_pdie_ucie_col.sv $U/ot_pdie_ucie_col_w.sv $CS"
for m in 0 1 2; do
  ( d="$OUT/link_m$m"; mkdir -p "$d"
    $VL $VLF --top-module tb_pdie_ucie_col -GMODE=$m -GMUT=0 $LS -Mdir "$d/obj" > "$d/build.log" 2>&1 && "$d/obj/Vtb_pdie_ucie_col" > "$d/run.log" 2>&1
    echo "LINK MODE $m: $(grep -o 'TB_PDIE_UCIE_COL [A-Z]*' "$d/run.log" 2>/dev/null | tail -1)" ) > "$OUT/link_m$m.res" &
done
for m in 1 2 3; do
  ( d="$OUT/linkmut_$m"; mkdir -p "$d"
    $VL $VLF --top-module tb_pdie_ucie_col -GMODE=0 -GMUT=$m $LS -Mdir "$d/obj" > "$d/build.log" 2>&1 && "$d/obj/Vtb_pdie_ucie_col" > "$d/run.log" 2>&1
    echo "LINK MUT $m: $(grep -o 'TB_PDIE_UCIE_COL [A-Z]*' "$d/run.log" 2>/dev/null | tail -1)" ) > "$OUT/linkmut_$m.res" &
done
wait
cat "$OUT/audit.res" "$OUT"/lp_m*.res "$OUT"/link_m*.res "$OUT"/linkmut_*.res
rc=0; grep -q "AUDIT PASS" "$OUT/audit.res" || rc=1
grep -q "LP_LOCKSTEP PASS" "$OUT/lp_m0.res" || rc=1; grep -q "LP_LOCKSTEP FAIL" "$OUT/lp_m4.res" || rc=1
for m in 0 1 2; do grep -q "TB_PDIE_UCIE_COL PASS" "$OUT/link_m$m.res" || rc=1; done
for m in 1 2 3; do grep -q "TB_PDIE_UCIE_COL FAIL" "$OUT/linkmut_$m.res" || rc=1; done
echo "UCIE_COL_ALL_EXIT $rc"; exit $rc
