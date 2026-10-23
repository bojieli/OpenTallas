#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
srcs=(rtl/test/qwen_dv/s8/tb_fdn_kept_selectors.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_split.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv)
for d in 4 8;do
 for phase in -80 0 80;do
  tag=d${d}p${phase}
  iverilog -g2012 -s tb_fdn_kept_selectors -Ptb_fdn_kept_selectors.D=$d -Ptb_fdn_kept_selectors.K=$((d/2)) -Ptb_fdn_kept_selectors.PHASE=$phase -o "$out/$tag" "${srcs[@]}" > "$out/${tag}_build.log" 2>&1
  vvp "$out/$tag" | tee "$out/$tag.log"
 done
done
for m in 1 2;do
 tag=m$m
 iverilog -g2012 -s tb_fdn_kept_selectors -Ptb_fdn_kept_selectors.MUT=$m -o "$out/$tag" "${srcs[@]}" > "$out/${tag}_build.log" 2>&1
 if vvp "$out/$tag" > "$out/$tag.log" 2>&1;then echo 'MUTANT ESCAPED';exit 1;fi
 grep FDN_SELECTOR_MISMATCH "$out/$tag.log"
done
