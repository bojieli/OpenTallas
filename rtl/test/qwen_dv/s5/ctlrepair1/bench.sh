#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
cmp ../generated2/helpers.sv ../generated2/mut11_helpers.sv
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_ctl_repair1 rtl/test/qwen_dv/s5/ctlsafe/ctl_gate2_snapshot.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv ../generated2/qfd_dv_s5_ctl_repair1.sv ../generated2/helpers.sv ../generated2/mut11.sv rtl/test/qwen_dv/s5/ctlrepair1/tb_ctl_repair1.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
"$O/obj/Vtb_ctl_repair1" > "$O/eq.log" 2>&1
"$O/obj/Vtb_ctl_repair1" +mutate > "$O/mut11.log" 2>&1
cat "$O/eq.log" "$O/mut11.log"
grep -q 'CTL_REPAIR_EQ PASS' "$O/eq.log"
grep -q 'CTL_REPAIR_EQ FAIL' "$O/mut11.log"
