#!/usr/bin/env bash
# run.sh OUT [MUT]
set -uo pipefail
cd "$(dirname "$0")/../../../../../../.."
O=${1:?out}; M=${2:-0}; mkdir -p "$O"; S=rtl/hbm_accel/generic/vm/static
iverilog -g2012 -s tb_q1core_pr -Ptb_q1core_pr.MUT=$M -o "$O/tb.vvp" $S/physical/q1core_pr/tb_q1core_pr.sv $S/physical/hfd_vms_bank_native_q1_core_pr.sv \
  $S/physical/hfd_vms_bank_native_q1_core.sv $S/physical/hfd_vms_bank_native_q1.sv $S/ot_vms_bank_static_strap.sv $S/ot_vms_ce_counter_pipe.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$O/build.log" 2>&1 || { tail -5 "$O/build.log"; echo "Q1CORE_PR EQUIV BUILDFAIL"; exit 1; }
vvp "$O/tb.vvp" | tail -5
