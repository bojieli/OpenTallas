#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su/native_vm
V=rtl/hbm_accel/generic/vm/static
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for variant in positive lg bank; do
 args=()
 case "$variant" in lg) args=(-GMUT_LG=1);; bank) args=(-GMUT_BANK=1);; esac
 "$vl" --binary --timing -O1 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_hbm_su_native_vm "${args[@]}" --Mdir "$out/obj_$variant" \
  "$S/tb_hbm_su_native_vm.sv" "$S/ot_hbm_su_native_vm.sv" \
  "$V/ot_hbm_vm_lg_static_split.sv" "$V/ot_hbm_vm_lg_static_bank.sv" "$V/ot_vms_bank_static.sv" \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build_$variant.log" 2>&1
 set +e
 "$out/obj_$variant/Vtb_hbm_su_native_vm" > "$out/$variant.log" 2>&1
 rc=$?
 set -e
 echo "exit=$rc" >> "$out/$variant.log"
 if [ "$variant" = positive ]; then
  [ "$rc" = 0 ]; grep -q 'SU_NATIVE_VM PASS' "$out/$variant.log"
  set +e
  "$out/obj_$variant/Vtb_hbm_su_native_vm" +MUT_CAL > "$out/calendar_mutant.log" 2>&1
  rc=$?
  set -e
  echo "exit=$rc" >> "$out/calendar_mutant.log"
  [ "$rc" != 0 ]; grep -q 'SU_NATIVE_VM FAIL' "$out/calendar_mutant.log"
 else
  [ "$rc" != 0 ]; grep -q 'SU_NATIVE_VM FAIL' "$out/$variant.log"
 fi
done
echo SU_NATIVE_VM_COMPONENT_GATE_PASS
