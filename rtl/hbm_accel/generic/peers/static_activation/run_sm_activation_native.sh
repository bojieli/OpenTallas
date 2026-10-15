#!/usr/bin/env bash
set -euo pipefail
out="${1:?output directory}";inputs="${2:-.}";mkdir -p "$out"
sources=(tb_sm_activation_native.sv ot_hbm_sm_activation_programmed_static.sv ot_hbm_sm_activation_static.sv ot_hbm_sm_aq_static.sv ot_vms_calendar_static.sv hfd_vms_bank_static_rg6wg2.sv ot_vms_bank_static.sv ot_hdc_fastfp_lat_f12.sv ot_hdc_fp32_f12.sv ot_hdc_fastfp.sv ot_hdc_prefix.sv ot_hdc_sfu.sv ot_hdc_delay.sv ot_sram_1r1w_1024x256_m2_r2c2.v ot_sram_1r1w_32x128_m1.v)
args=();for s in "${sources[@]}";do args+=("$inputs/$s");done
for mut in 0 1 2;do
 /usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_sm_activation_native -Ptb_sm_activation_native.MUT="$mut" -o "$out/gate-$mut.vvp" "${args[@]}" > "$out/compile-$mut.log" 2>&1
 set +e
 /usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/gate-$mut.vvp" > "$out/sim-$mut.log" 2>&1
 rc=$?
 set -e
 cat "$out/sim-$mut.log"
 if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q 'SM_ACTIVATION_NATIVE PASS' "$out/sim-$mut.log"
 else [[ $rc != 0 ]];grep -Eq 'native activation actual code SRAM beat payload mismatch|native activation fault' "$out/sim-$mut.log";fi
done
printf 'PASS actual native VM programme/AQ/code SRAM activation producer plus lane/buffer mutants\n'
