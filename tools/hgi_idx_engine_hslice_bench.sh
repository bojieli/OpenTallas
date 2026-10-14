#!/bin/bash
set -eu
out=$1
mkdir -p "$out"
vl="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
[ -x "$vl" ] || vl=verilator
src=(rtl/hdc/v41x/ot_hdc_v41x_idx_engine_hslice.sv rtl/hdc/v41x/ot_hdc_v41x_idx_chunk_el.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/test/hbm_idx_chunk_el/tb_hgi_idx_engine_hslice.sv)
for mut in 0 2; do
 "$vl" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-PINMISSING \
 --top-module tb_hgi_idx_engine_hslice -GMUT="$mut" -Mdir "$out/obj$mut" "${src[@]}" -j 8 > "$out/build$mut.log" 2>&1
 set +e
 "$out/obj$mut/Vtb_hgi_idx_engine_hslice" > "$out/run$mut.log" 2>&1
 rc=$?
 set -e
 grep 'HGI_IDX_ENGINE_HSLICE' "$out/run$mut.log"
 if [ "$mut" = 0 ]; then
   [ "$rc" = 0 ] && grep -q 'errors=0.*PASS' "$out/run$mut.log"
 else
   [ "$rc" != 0 ] && grep -q 'HGI_IDX_ENGINE_HSLICE.*FAIL' "$out/run$mut.log"
 fi
done
echo 'HGI_IDX_ENGINE_HSLICE GATE PASS'
