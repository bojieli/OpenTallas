#!/usr/bin/env bash
# HBM-KITS-A 10-18: ot_hbm_argmax_static_sw_vm unit bench split out of run_attn_0030.sh (argmax part only) so the closure
# job carries one expect=pass bench and one expect=fail bench per mutant.  usage: run_argmax_sw_vm.sh OUT [MUT]
#  tb_argmax_sw_vm: ot_hbm_argmax_static_sw_vm vs ot_hbm_argmax_static_sw, 300 random records on a fixed-latency
#  VM/record-client model (RD 7, ACK 11 edges).  MUT0 PASS; MUT1 (STREAM record passes through: hangs) / MUT2 (all
#  records illegal) FAIL.  Last line: "ARGMAX_SW_VM_BENCH MUT=<m> PASS|FAIL".
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); m=${2:-0}; mkdir -p "$out"
A=(rtl/test/hbm_netlist_v16/tb_argmax_sw_vm.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv
   rtl/hbm_accel/generic/ot_hbm_argmax_static_sw.sv rtl/hbm_accel/generic/ot_hbm_argmax_static.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
iverilog -g2012 -DMUT=$m -DRD=7 -DACKD=11 -DNREC=300 -o "$out/a$m" "${A[@]}" || { echo "ARGMAX_SW_VM_BENCH MUT=$m BUILD_ERROR"; exit 2; }
vvp -n "$out/a$m" > "$out/argmax_mut$m.log" 2>&1
tail -5 "$out/argmax_mut$m.log"
if grep -q "^ARGMAX_SW_VM PASS" "$out/argmax_mut$m.log"; then echo "ARGMAX_SW_VM_BENCH MUT=$m PASS"; exit 0
elif grep -q "^ARGMAX_SW_VM FAIL" "$out/argmax_mut$m.log"; then echo "ARGMAX_SW_VM_BENCH MUT=$m FAIL"; exit 1
else echo "ARGMAX_SW_VM_BENCH MUT=$m NO_VERDICT"; exit 3; fi
