#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_native_ctl_entry --Mdir obj src/ot_rst_relay.sv src/ot_s81sl_rstopt_xo.sv src/ot_s81sl_xrt.sv tb_native_ctl_entry.sv > build.log 2>&1
obj/Vtb_native_ctl_entry > base.log 2>&1
set +e
obj/Vtb_native_ctl_entry +bad_payload > payload.log 2>&1
p=$?
obj/Vtb_native_ctl_entry +bad_age > age.log 2>&1
a=$?
set -e
cat base.log
if [ "$p" -eq 0 ] || [ "$a" -eq 0 ]; then echo MUTANT_NOT_CAUGHT; exit 1; fi
echo NATIVE_CTL_ENTRY_CONTROLS_PASS
