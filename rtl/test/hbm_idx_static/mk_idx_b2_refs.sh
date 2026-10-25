#!/usr/bin/env bash
# HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): reference modules for the B2 strap benches, extracted UNCHANGED from the
# as-built r18h5 source commit (d34578d6f = the die closure bundle the r18h5 die binds) and renamed:
#   ot_hbm_idx_rootctl_static_am_ref   (as built)        ot_hbm_idx_rootctl_static_am_ref3 (as built, literal SID 0 -> 3)
#   ot_hbm_argmax_static_sw_vm_r2_ref  (as built)        ot_hbm_argmax_static_sw_vm_r2_ref3 (as built, literal sid 0 -> 3)
#   ot_hbm_idx_selector_static_sel{,_core}_ref           ot_hbm_idx_topk_link_static{,_core}_ref
# usage: mk_idx_b2_refs.sh OUTDIR   (run inside a checkout of the repo that has commit d34578d6f)
set -euo pipefail
out=${1:?outdir}; mkdir -p "$out"; S=${ASBUILT:-d34578d6f}
g() { git show "$S:$1"; }
g rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv | sed 's/^module ot_hbm_idx_rootctl_static_am /module ot_hbm_idx_rootctl_static_am_ref /' > "$out/rootctl_ref.sv"
g rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv | sed -e 's/^module ot_hbm_idx_rootctl_static_am /module ot_hbm_idx_rootctl_static_am_ref3 /' \
  -e "s/^ localparam \[1:0\] SID = 2'd0;/ localparam [1:0] SID = 2'd3;/" > "$out/rootctl_ref3.sv"
g rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv | sed 's/^module ot_hbm_argmax_static_sw_vm_r2 /module ot_hbm_argmax_static_sw_vm_r2_ref /' > "$out/argmax_ref.sv"
g rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv | sed -e 's/^module ot_hbm_argmax_static_sw_vm_r2 /module ot_hbm_argmax_static_sw_vm_r2_ref3 /' \
  -e "s/^    localparam \[1:0\] sid = 2'd0;/    localparam [1:0] sid = 2'd3;/" > "$out/argmax_ref3.sv"
g rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv | sed -e 's/ot_hbm_idx_selector_static_sel_core/ot_hbm_idx_selector_static_sel_core_ref/g' \
  -e 's/^module ot_hbm_idx_selector_static_sel #/module ot_hbm_idx_selector_static_sel_ref #/' > "$out/selector_ref.sv"
g rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv | sed -e 's/ot_hbm_idx_topk_link_static_core/ot_hbm_idx_topk_link_static_core_ref/g' \
  -e 's/^module ot_hbm_idx_topk_link_static #/module ot_hbm_idx_topk_link_static_ref #/' > "$out/link_ref.sv"
# each substitution must have hit exactly once
c() { n=$(grep -c "$2" "$out/$1"); [ "$n" = "$3" ] || { echo "REF_BUILD_FAIL $1 '$2' count $n != $3"; exit 2; }; }
c rootctl_ref.sv '^module ot_hbm_idx_rootctl_static_am_ref ' 1
c rootctl_ref3.sv "^ localparam \[1:0\] SID = 2'd3;" 1
c argmax_ref.sv '^module ot_hbm_argmax_static_sw_vm_r2_ref ' 1
c argmax_ref3.sv "^    localparam \[1:0\] sid = 2'd3;" 1
c selector_ref.sv '^module ot_hbm_idx_selector_static_sel_core_ref ' 1
c selector_ref.sv '^module ot_hbm_idx_selector_static_sel_ref ' 1
c link_ref.sv '^module ot_hbm_idx_topk_link_static_core_ref ' 1
c link_ref.sv '^module ot_hbm_idx_topk_link_static_ref ' 1
echo "IDX_B2_REFS OK $S -> $out"
