#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for mode in provider provider_K provider_STAGE;do
 opts=()
 if [[ "$mode" != provider ]];then opts+=("+define+MUT_${mode#provider_}");fi
 verilator --binary --timing -j 2 -Wno-fatal "${opts[@]}" --top-module provider_tb --Mdir "obj_$mode" provider_tb.sv mechanism_tb.sv original_publish.sv original_sram.v source/{059_qfd_fwd_lane,005_ot_hdc_cg,058_qfd_embedding_word_provider,085_qkd_embedding_static_core_store,086_qkd_embedding_static_preload_face}.sv >"build_$mode.log" 2>&1
 set +e
 "./obj_$mode/Vprovider_tb" >"run_$mode.log" 2>&1
 result=$?
 set -e
 echo "$result" > "exit_$mode.txt"
done
