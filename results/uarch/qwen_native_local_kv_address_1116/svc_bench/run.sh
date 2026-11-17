#!/bin/bash
# usage: run.sh REPO_ROOT WORKDIR   (Verilator 5.050; run via ot-run). Builds adapter ON and OFF wrappers, runs 9 cases each.
set -euo pipefail
R=$(cd "$1" && pwd);W=$2;H=$(cd "$(dirname "$0")" && pwd);mkdir -p $W;cp -r $H/* $W/
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S="rtl/qwen_split/qfd_native59_svc_obs1.sv rtl/qwen_split/qfd_native59_svc.sv rtl/qwen_split/qfd_native59_static_service.sv rtl/qwen_split/qfd_native59_static_service_obs1.sv rtl/qwen_split/mu/qfd_status_obs_hold_chunk.sv rtl/qwen_split/qfd_native59_mctx_helpers.sv rtl/qwen_split/qfd_native59_command_context.sv rtl/qwen_split/qfd_native59_q_export_control.sv rtl/qwen_split/qfd_native59_record_endpoint.sv rtl/qwen_split/qfd_kvn_static_transport.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv"
A="";for f in $S;do A="$A $R/$f";done;cd $W
for AD in 1 0;do $VL --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_svc_local_dim -GADAPTER=$AD -Mdir obj$AD tb_svc_local_dim.sv $A >build$AD.log 2>&1;python3 -I run_cases.py $AD||true;done
