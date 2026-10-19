#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
python3 tools/s81_dv/layer_prog/qf_producer/compile_headers.py --out "$out/input"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
src=(rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fastfp.sv
rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_f12.sv
rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv
rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv
rtl/hdc/v41x/ot_dsrom_su_add6.sv
rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv
rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv
tools/s81_dv/layer_prog/qf_producer/tb_qf_config.sv)
sha256sum "${src[@]}" tools/s81_dv/layer_prog/qf_producer/compile_headers.py > "$out/sources.sha256"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_qf_config --Mdir "$out/obj" "${src[@]}" --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$out/build.log" 2>&1
for tag in 0 1 53 127 128 213 254 255;do
 "$out/obj/Vtb_qf_config" +DIR="$out/input" +TAG="$tag" > "$out/tag_${tag}.log" 2>&1
 grep QF_CONFIG_PASS "$out/tag_${tag}.log"
done
for mut in 1 2 3 4 5 6 7;do
 set +e
 "$out/obj/Vtb_qf_config" +DIR="$out/input" +TAG=53 +MUT="$mut" > "$out/mut_${mut}.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q QF_CONFIG_FAIL "$out/mut_${mut}.log";then
  echo "MUTANT_NOT_CAUSAL $mut $rc";exit 1
 fi
 echo "CAUSAL_MUTANT_FAIL $mut"
done
echo QF_CONFIG_COMPONENT_PASS
