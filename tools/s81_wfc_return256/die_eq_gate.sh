#!/bin/bash
# S-DIE-WFC 2026-10-16: Verilator gate of tb_die_wfc_return256_eq.sv (die u_wfc --wfc-return256 vs the frozen u_wfc).
# usage: die_eq_gate.sh OUT_DIR   (run from the source root; SEEDS / RPADS override the defaults)
# Every RPAD x {base: must PASS, MUT_HIGH and MUT_TAIL: must FAIL on a comparison (not on coverage)}; exit 0 only when
# all verdicts are as required.
set -uo pipefail
OUT=$1; mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
SRC="$V/dsfd_vm_static_wfc.sv $V/dsfd_vm_static_wfc_select256.sv $V/dsfd_vm_wfc_return256.sv $V/dsfd_vm_native_valid_diag.sv
     $V/ot_s81_vm_x34.sv $V/ot_s81_vm_x43.sv $V/ot_s81_vm_fault_transports.sv tools/s81_wfc_return256/tb_die_wfc_return256_eq.sv"
rc=0
for rp in ${RPADS:-0 2}; do
  for mut in base S81_RETURN256_MUT_HIGH S81_RETURN256_MUT_TAIL; do
    d="$OUT/rp${rp}_$mut"; mkdir -p "$d"
    defs="+define+RPAD=$rp"; [ "$mut" = base ] || defs="$defs +define+$mut"
    if ! verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_die_wfc_return256_eq \
         $defs -Mdir "$d/obj" $SRC > "$d/build.log" 2>&1; then
      echo "BUILD_FAIL rp=$rp $mut (see $d/build.log)"; tail -5 "$d/build.log"; rc=1; continue
    fi
    for seed in ${SEEDS:-1 2 3}; do
      "$d/obj/Vtb_die_wfc_return256_eq" +seed=$seed > "$d/seed$seed.log" 2>&1; st=$?
      res=$(grep -E "PASS|MISMATCH|fault|COVERAGE" "$d/seed$seed.log" | head -1)
      if [ "$mut" = base ]; then
        if [ $st -eq 0 ] && grep -q "DIE_WFC_RETURN256_EQ PASS" "$d/seed$seed.log"; then echo "PASS   rp=$rp $mut seed=$seed: $res"
        else echo "WRONG  rp=$rp $mut seed=$seed must PASS: st=$st $res"; rc=1; fi
      else
        if [ $st -ne 0 ] && grep -qE "MISMATCH|fault rise|without reference" "$d/seed$seed.log"; then echo "FAILS  rp=$rp $mut seed=$seed (required): $res"
        else echo "WRONG  rp=$rp $mut seed=$seed must FAIL: st=$st $res"; rc=1; fi
      fi
    done
  done
done
echo "DIE_EQ_GATE rc=$rc"
exit $rc
