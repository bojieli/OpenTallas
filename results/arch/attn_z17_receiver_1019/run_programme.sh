#!/bin/bash
set -euo pipefail
printf 'REAL_PROGRAMME_SIM_START ';date -u --iso-8601=seconds
iverilog -V > programme.iverilog.version.log 2>&1
iverilog -g2012 -s tb_kvs_attn_land_pair -o programme.vvp qkd_native59_descriptor_producer.sv qkd_native59_command_guard.sv qkd_native_attention_record.sv qkd_native_attention_static_ctl.sv qkd_native_attention_programme.sv qkd_native_attention_static_ctl_z17.sv qkd_native_attention_programme_z17.sv qkd_attn_service_root.sv qkd_attn_result_face_s.sv tb_programme_z17.sv > programme.compile.log 2>&1
for m in {0..15};do
 vvp programme.vvp +MODE=$m > programme.mode$m.log 2>&1
 tail -4 programme.mode$m.log
done
printf 'REAL_PROGRAMME_SIM_EXIT 0 ';date -u --iso-8601=seconds
