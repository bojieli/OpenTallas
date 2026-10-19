#!/bin/bash
# LH-P3UNITS/UNIONTILE 10-19: PER-QUADRANT factored union dispatch (head tap + 4 landed links + 4 x ot_hnx_union_qtile =
# dispatcher copy + metadata macro + 7-macro kernel store) behind the ACTUAL IDX.UNION + SW VM slice.
# Fleet only (ot-run); Verilator 5.050 = the closure daemon's.  Usage: union_quad_bench.sh OUT [MODES]  (default 0..5)
#   0 PASS: every copy launches on the central golden edge (LQ 28/20/12/6) + exact kernel words + 1 abort per IDX fault
#   1 neighbouring-cardinality kernel           -> UNION_FACTORED_WRONG_VARIANT
#   2 inclusive prefix                          -> UNION_FACTORED_WRONG_START or _MISSING
#   3 U-only N-row kernel                       -> UNION_FACTORED_WRONG_VARIANT
#   4 no origin prediction (start at forwarded union_v = central latency at the quadrant) -> _MISSING / _WRONG_START
#   5 kernel store: loop-2 descriptor without half-word packing -> UNION_QUAD_KSTORE_WORD
set -eu
O=$(realpath -m "${1:-quad_out}"); MODES="${2:-0 1 2 3 4 5}"; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$O/verilator.txt"
VS=rtl/hbm_accel/generic/vm/static
SRC=(rtl/hbm_next/idx/ot_hnx_idx_union_static.sv rtl/hbm_next/control/ot_hnx_union_tap.sv
 rtl/hbm_next/control/ot_hnx_union_qdisp.sv rtl/hbm_next/control/ot_hnx_union_kstore.sv
 rtl/hbm_next/control/ot_hnx_union_qtile.sv rtl/hbm_next/control/tb_hnx_union_quad.sv
 rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 $VS/hfd_hgi_vms_static.sv $VS/ot_vms_slice_static.sv $VS/ot_vms_hub_static.sv $VS/ot_vms_bank_static.sv
 $VS/ot_vms_rstop_static.sv $VS/ot_vms_rcl_static.sv $VS/ot_vms_status_static.sv
 physical/hbm_next/union/macros/hnx_sram_1r1w_1024x256_r43/hnx_sram_1r1w_1024x256_r43.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
GEN=(tools/hbm_next/union_factored_vectors.py tools/hbm_next/hnx_idx_union_vectors.py tools/hbm_next/union_variants.py
 tools/hbm_next/isa_rows.py tools/hbm_idx_topk_static_vectors.py tools/hbm_next/union_quad_bench.sh tools/hgi_sim/machine.py tools/hbm_generic_iface.py
 tools/hdc_isa_v41.py tools/hdc_golden.py)
sha256sum "${SRC[@]}" "${GEN[@]}" > "$O/sources.sha256"
OT_UF_KB=0x040,0x080,0x3ff python3 tools/hbm_next/union_factored_vectors.py "$O/vectors" 0 > "$O/vector.log"
for m in $MODES; do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_union_quad -GPMUT=$m \
  -Mdir "$O/obj$m" "${SRC[@]}" > "$O/build$m.log" 2>&1
 set +e; (cd "$O/vectors"; "$O/obj$m/Vtb_hnx_union_quad") > "$O/run$m.log" 2>&1; rc=$?; set -e
 case $m in
  0) [ "$rc" = 0 ]; grep -q 'UNION_QUAD PASS' "$O/run$m.log";;
  2|4) [ "$rc" != 0 ]; grep -E -q 'UNION_FACTORED_(WRONG_START|MISSING)' "$O/run$m.log";;
  5) [ "$rc" != 0 ]; grep -q 'UNION_QUAD_KSTORE_WORD' "$O/run$m.log";;
  *) [ "$rc" != 0 ]; grep -q 'UNION_FACTORED_WRONG_VARIANT' "$O/run$m.log";;
 esac
 echo "quad PMUT$m expected exit=$rc"
done
echo "UNION_QUAD_BENCH ALL EXPECTED $MODES"
