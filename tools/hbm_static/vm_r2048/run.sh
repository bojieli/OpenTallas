#!/bin/bash
set -euo pipefail
O=${1:?fresh output root}
D=rtl/hbm_accel/generic/vm/static/faces_q0
N=rtl/hbm_accel/generic/vm/static/faces_q0_r2048
B=tools/hbm_static/vm_r2048
mkdir -p "$O"
for c in positive high_alias mirror_alias;do
 mut=0;case "$c" in high_alias)mut=5;;mirror_alias)mut=6;;esac
 iverilog -g2012 -s tb_vm_r2048 -Ptb_vm_r2048.MUT=$mut -o "$O/$c.vvp" "$D/hfd_vms_bank_native_q0_faces.sv" "$D/ot_vms_bank_q0_faces_core.sv" "$D/ot_vms_bank_q0_faces_body.sv" "$N"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v "$B/tb.sv" >"$O/$c.build.log" 2>&1
 rc=0;vvp "$O/$c.vvp" >"$O/$c.log" 2>&1||rc=$?
 if [ "$c" = positive ];then
  test "$rc" = 0;grep 'VM_R2048 PASS' "$O/$c.log"
 else
  test "$rc" != 0;grep -q FATAL "$O/$c.log";echo "MUTANT_CAUGHT $c"
 fi
done
