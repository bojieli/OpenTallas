#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
R=$PWD
mkdir -p face
python3 tools/qwen_kv_die/attn_safe_control_1019/build_face_bench.py face
for mutant in 0 1 2;do
 mkdir -p face/m$mutant
 cp src/rtl/qwen_sys/kv_bootage_20261019/qkd_attn_result_face_sc.sv face/m$mutant/candidate.sv
 if [ "$mutant" = 1 ];then sed -i 's/assign selected=fire\&delta;/assign selected=(~fire)\&delta;/' face/m$mutant/candidate.sv;fi
 if [ "$mutant" = 2 ];then sed -i 's/assign delta=rdata\[hb\]\^hold_data\[hb\];/assign delta=rdata[hb]|hold_data[hb];/' face/m$mutant/candidate.sv;fi
 verilator --version > face/m$mutant/build.log
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_face --Mdir "$R/face/m$mutant/obj" -o vtb face/tb_face.sv src/rtl/qwen_sys/kv_bootage_20261019/qkd_attn_result_face_sb.sv face/m$mutant/candidate.sv >> face/m$mutant/build.log 2>&1
 set +e
 face/m$mutant/obj/vtb > face/m$mutant/sim.log 2>&1
 rc=$?
 set -e
 if [ "$mutant" = 0 ];then test "$rc" = 0;grep '^ATTN_FACE_EXACT PASS' face/m$mutant/sim.log;else test "$rc" != 0;grep '^ATTN_FACE_MISMATCH' face/m$mutant/sim.log;fi
done
