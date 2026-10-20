#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 tools/qwen_kv_die/attn_safe_control_1019/build_native_bench.py
for m in 0 1;do
 f=candidate/qkd_kvs_attn_safe_control.v
 if [ "$m" = 1 ];then f=native/candidate_mut1.v;fi
 mkdir -p native/m$m
 verilator --version > native/m$m/build.log
 verilator --binary --timing -j 8 --x-initial unique -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_native --Mdir "$PWD/native/m$m/obj" -o vtb native/tb_native.sv native/models.v "$f" >> native/m$m/build.log 2>&1
 set +e
 native/m$m/obj/vtb +verilator+rand+reset+2 +verilator+seed+192361 > native/m$m/sim.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep '^ATTN_NATIVE_COHORT PASS' native/m$m/sim.log;else test "$rc" != 0;grep '^NATIVE_COHORT_MISMATCH' native/m$m/sim.log;fi
done
