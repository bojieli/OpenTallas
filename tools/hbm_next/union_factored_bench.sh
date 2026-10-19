#!/bin/bash
# LH-P3UNITS/UNIONVAR 10-19: factored ordered-cardinality dispatcher behind the ACTUAL IDX.UNION + SW VM slice.
# Fleet only (ot-run); Verilator 5.050 = the closure daemon's.  PMUT 0 must PASS; PMUT 1/2/3 must FAIL with their text:
#   1 neighbouring-cardinality kernel (wrong variant)  -> UNION_FACTORED_WRONG_VARIANT
#   2 inclusive prefix (wrong start offset)            -> UNION_FACTORED_WRONG_START or _MISSING (late launch)
#   3 U-only N-row kernel for every expert (wrong variant) -> UNION_FACTORED_WRONG_VARIANT
set -eu
O=$(realpath -m "${1:-factored_out}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$O/verilator.txt"
VS=rtl/hbm_accel/generic/vm/static
SRC=(rtl/hbm_next/idx/ot_hnx_idx_union_static.sv rtl/hbm_next/control/ot_hnx_union_prefix.sv
 rtl/hbm_next/control/tb_hnx_union_factored.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 $VS/hfd_hgi_vms_static.sv $VS/ot_vms_slice_static.sv $VS/ot_vms_hub_static.sv $VS/ot_vms_bank_static.sv
 $VS/ot_vms_rstop_static.sv $VS/ot_vms_rcl_static.sv $VS/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
GEN=(tools/hbm_next/union_factored_vectors.py tools/hbm_next/hnx_idx_union_vectors.py tools/hbm_next/union_variants.py
 tools/hbm_next/isa_rows.py tools/hbm_idx_topk_static_vectors.py)
sha256sum "${SRC[@]}" "${GEN[@]}" > "$O/sources.sha256"
python3 tools/hbm_next/union_factored_vectors.py "$O/vectors" 0 > "$O/vector.log"
for m in 0 1 2 3; do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_union_factored -GPMUT=$m \
  -Mdir "$O/obj$m" "${SRC[@]}" > "$O/build$m.log" 2>&1
 set +e; (cd "$O/vectors"; "$O/obj$m/Vtb_hnx_union_factored") > "$O/run$m.log" 2>&1; rc=$?; set -e
 case $m in
  0) [ "$rc" = 0 ]; grep -q 'UNION_FACTORED PASS' "$O/run$m.log";;
  2) [ "$rc" != 0 ]; grep -E -q 'UNION_FACTORED_(WRONG_START|MISSING)' "$O/run$m.log";;
  *) [ "$rc" != 0 ]; grep -q 'UNION_FACTORED_WRONG_VARIANT' "$O/run$m.log";;
 esac
 echo "factored PMUT$m expected exit=$rc"
done
echo "UNION_FACTORED_BENCH ALL EXPECTED"
