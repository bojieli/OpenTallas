#!/usr/bin/env bash
set -euo pipefail
contract=${1:?contract}; out=${2:?output}; mkdir -p "$out"; out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 tools/hbm_die_v16/bench_vm_fault_l16.py "$contract" "$out"
verilator --version
sources=(rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_fault_leaf.sv rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv rtl/hbm_accel/host_static_20261015/ot_hbm_status_join.sv rtl/hbm_accel/host_static_20261015/ot_hbm_status_join_fa.sv)
for mut in 0 1 2; do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT=$mut --top-module tb_vm_fault_l16 --Mdir "$out/obj$mut" -o tb "$out/tb_vm_fault_l16.sv" "${sources[@]}" > "$out/build$mut.log" 2>&1
 if "$out/obj$mut/tb" > "$out/run$mut.log" 2>&1; then
  test "$mut" = 0 || { echo "VM_FAULT_MUTANT_SURVIVED $mut"; exit 1; }
  grep '^VM_FAULT_PASS cases=84' "$out/run$mut.log"
 else
  test "$mut" != 0 || { tail -10 "$out/run$mut.log"; exit 1; }
  grep 'VM_FAULT_FAIL' "$out/run$mut.log"
 fi
done
