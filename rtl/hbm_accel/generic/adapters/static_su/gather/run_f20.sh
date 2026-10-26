#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
O=$(realpath -m "${1:?output}");mkdir -p "$O"
D=rtl/hbm_accel/generic/adapters/static_su/gather
B=rtl/hbm_accel/generic/vm/static
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for m in ${MUTANTS:-0 1 2 3};do
 "$VL" --binary --timing -j 8 -Wno-fatal --top-module tb_indexed_scalar_f20 -GMUT=$m --Mdir "$O/obj$m" -o vtb rtl/lib/ot_rst_relay.sv "$D/ot_hbm_su_indexed_scalar_banked.sv" "$D/ot_hbm_su_indexed_scalar.sv" "$D/ot_hbm_su_indexed_scalar_f20.sv" "$D/tb_indexed_scalar_f20.sv" "$B/ot_static_program_target.sv" "$B/faces_q0/hfd_vms_bank_native_q0_faces.sv" "$B/faces_q0/ot_vms_bank_q0_faces_core.sv" "$B/faces_q0/ot_vms_bank_q0_faces_body.sv" "$B/ot_vms_ce_counter_pipe.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$O/build$m.log" 2>&1
 set +e
 run_args=()
 if [[ -n ${FIXTURE:-} ]];then run_args+=("+FIXTURE=$FIXTURE" "+ROWS=${ROWS:?rows dir}");fi
 "$O/obj$m/vtb" "${run_args[@]}" > "$O/run$m.log" 2>&1
 rc=$?
 set -e
 cat "$O/run$m.log"
 if [[ $m = 0 ]];then test $rc = 0;grep -q 'GATHER_F20_CURRENT PASS' "$O/run$m.log";else test $rc != 0;grep -q 'GATHER_F20_CURRENT FAIL' "$O/run$m.log";fi
done
