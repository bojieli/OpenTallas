#!/usr/bin/env bash
# Full native DS candidate dispatcher component gate. Run on admitted fleet host.
set -u
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
out=$(realpath -m -- "${1:?output directory required}")
mkdir -p -- "$out"
cd -- "$repo"
src=(rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_native_ds_dispatch.sv rtl/test/hbm_generic_20261009/tb_hgi_idx_native_ds_dispatch.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
for variant in golden mutant; do
 extra=()
 if [ "$variant" = mutant ]; then extra=(-Ptb_hgi_idx_native_ds_dispatch.MUTANT=1); fi
 /usr/bin/time -v -o "$out/$variant.compile.time" iverilog -g2012 -s tb_hgi_idx_native_ds_dispatch "${extra[@]}" -o "$out/$variant.vvp" "${src[@]}" > "$out/$variant.compile.log" 2>&1
 rc=$?
 echo "$rc" > "$out/$variant.compile.rc"
 if [ "$rc" != 0 ]; then exit 2; fi
 /usr/bin/time -v -o "$out/$variant.runtime.time" vvp "$out/$variant.vvp" > "$out/$variant.runtime.log" 2>&1
 rc=$?
 echo "$rc" > "$out/$variant.runtime.rc"
 if [ "$variant" = golden ] && [ "$rc" != 0 ]; then exit 1; fi
 if [ "$variant" = mutant ] && [ "$rc" = 0 ]; then exit 1; fi
done
echo PASS_HGI_NATIVE_INDEX_GATE
