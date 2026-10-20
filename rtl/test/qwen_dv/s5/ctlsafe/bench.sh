#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_ctl_bounded rtl/test/qwen_dv/s5/ctlsafe/ctl_gate2_snapshot.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv ../construct3/qfd_dv_s5_ctl_bounded4.sv ../construct3/qfd_dv_s5_ctl_bounded_helpers.sv rtl/test/qwen_dv/s5/ctlsafe/tb_ctl_bounded.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
"$O/obj/Vtb_ctl_bounded" > "$O/eq.log" 2>&1
"$O/obj/Vtb_ctl_bounded" +mutate > "$O/mut.log" 2>&1
cat "$O/eq.log" "$O/mut.log"
grep -q 'CTL_BOUND_EQ PASS' "$O/eq.log"
grep -q 'CTL_BOUND_EQ FAIL' "$O/mut.log"
