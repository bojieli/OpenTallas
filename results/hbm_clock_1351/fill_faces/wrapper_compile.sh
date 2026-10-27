#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
D=/srv/opentallas-scratch2/claude/codex-hbm-clock-1351
S=/srv/opentallas-scratch2/claude/wt/codex-hbm-clock-1351/rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_n_faces.sv
yosys -Q -p "read_verilog -lib $D/kit_vmdel_centre/lec/bb.v; read_verilog -sv $D/native_capture_65315.sv $S; hierarchy -check -top ot_hbm_svc_vmdel_lane_n_faces -chparam PAYLOAD_BANK_CAPTURE 1; proc; check -assert; stat" > "$D/wrapper_compile.log" 2>&1
echo WRAPPER_NATIVE_CAPTURE_PARAM1_COMPILE_PASS
