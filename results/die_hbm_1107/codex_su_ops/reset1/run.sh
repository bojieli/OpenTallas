#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O0 -j 2 -Wno-fatal -Wno-lint -Wno-style -DCYC=60000 --top-module tb -Mdir o -o sim tb.sv old_core.sv old_sh.sv rtl/ot_hgi_sfu_opsa_rest.sv rtl/ot_hgi_sfu_opsa_rest__fshell.sv rtl/ot_hbm_face_reg.sv > build.log 2>&1
./o/sim > run.log 2>&1
