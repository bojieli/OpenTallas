#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --top-module tb -Wno-fatal -j 2 --Mdir obj_dir ../../rtl/hbm_accel/cores_split/reform_1105s/glue/ot_vms_glue_pc.sv status_reference.sv mutants.sv tb.sv > build.log 2>&1
./obj_dir/Vtb | tee result.log
