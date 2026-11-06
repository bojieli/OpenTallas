#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --top-module tb_default -Wno-fatal -j 2 --Mdir obj_default_branch ../../rtl/hbm_accel/cores_split/reform_1105s/glue/ot_vms_glue_pc.sv status_reference.sv status_enabled_reference.sv tb_default.sv > default_build.log 2>&1
./obj_default_branch/Vtb_default | tee default_result.log
