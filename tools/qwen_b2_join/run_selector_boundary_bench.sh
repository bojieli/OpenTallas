#!/bin/bash
set -eu
out=${1:?output-directory};mkdir -p "$out"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cat > "$out/sources.f" <<'SRC'
rtl/hdc/ot_hdc_prefix.sv
rtl/hdc/ot_hdc_fastfp.sv
rtl/hdc/ot_hdc_delay.sv
rtl/hdc/ot_hdc_fp32_add_lat.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
rtl/hdc/ot_qwen_w12_matvec.sv
rtl/hdc/ot_qwen_me_spine_h_w12.sv
rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv
rtl/qwen_split/qfd_static_selector_fork4.sv
rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv
tools/qwen_b2_join/tb_b2_selector_boundary.sv
SRC
sha256sum $(cat "$out/sources.f") > "$out/source.sha256"
"$VL" --binary --timing -j 4 -O1 -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -Irtl/hdc --top-module tb_b2_selector_boundary --Mdir "$out/obj" -f "$out/sources.f" > "$out/build.log" 2>&1
"$out/obj/Vtb_b2_selector_boundary" > "$out/base.log" 2>&1
for b in 1 2 3 4 5 6 7 8;do
 if "$out/obj/Vtb_b2_selector_boundary" +MUT_BANK=$b > "$out/mut$b.log" 2>&1;then echo "FAIL bank$b selector+1 not rejected";exit 1;fi
 grep -q "MISMATCH bank$((b-1))" "$out/mut$b.log"
 if "$out/obj/Vtb_b2_selector_boundary" +MUT_BANK=$b +SEL_ONLY=1 > "$out/selmut$b.log" 2>&1;then echo "FAIL bank$b sel-only+1 not rejected";exit 1;fi
 grep -q "MISMATCH bank$((b-1))" "$out/selmut$b.log"
done
echo 'PASS selector boundary + eight bus+1 and eight sel-only+1 mutants rejected'
