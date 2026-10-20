#!/bin/bash
# QW-SLICE7-CTL kit bench (repair4): lockstep of the committed repair4 netlist vs the ctl_gate2 behavioural snapshot
# (151,677 values / 8,000 edges, two mid-run resets); MODE=mut runs the committed real MUT11 netlist (collective-command
# bit defect) and must FAIL.  All inputs are in-repo; Verilator 5.050 (daemon pin).
set -euo pipefail
O=$1; MODE=${2:-eq}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v "$V" >/dev/null 2>&1 || V=verilator
"$V" --version
K=rtl/test/qwen_dv/s5/ctlrepair1/kit4
zcat $K/mut11.sv.gz > "$O/mut11.sv"
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
  --top-module tb_ctl_repair4 rtl/test/qwen_dv/s5/ctlsafe/ctl_gate2_snapshot.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv \
  rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4.sv rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_helpers.sv "$O/mut11.sv" \
  rtl/test/qwen_dv/s5/ctlrepair1/tb_ctl_repair4.sv -Mdir "$O/obj" > "$O/build.log" 2>&1 || { tail -40 "$O/build.log"; exit 2; }
if [ "$MODE" = mut ]; then "$O/obj/Vtb_ctl_repair4" +mutate 2>&1 | tee "$O/mut11.log"; else "$O/obj/Vtb_ctl_repair4" 2>&1 | tee "$O/eq.log"; fi
