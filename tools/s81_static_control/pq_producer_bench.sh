#!/usr/bin/env bash
set -u
mode=$1
out=$2
mkdir -p "$out"
case "$mode" in
 pass) extra=() ;;
 slot) extra=(--mut PQSLOT) ;;
 prime) extra=(--mut PRIME) ;;
 hostdrop) extra=(--mut HOSTDROP) ;;
 *) echo "PQPRODUCER BUILD_FAIL unknown mode"; exit 2 ;;
esac
if [ "${3:-}" = phase-safe ]; then extra+=(--host-phase-safe); fi
if [ "${3:-}" = boot300 ]; then extra+=(--host-boot300); fi
python3 tools/s81/pq_canonical_pins_gate.py --sequenced --work "$out" "${extra[@]}" > "$out/driver.log" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then cat "$out/driver.log"; echo "PQPRODUCER BUILD_FAIL $mode"; exit 2; fi
cat "$out/driver.log"
if [ "$mode" = pass ]; then
 echo "PQPRODUCER PASS"; exit 0
fi
if ! grep -q 'SEQUENCED FAIL' "$out/run.log"; then echo "PQPRODUCER MUTANT_ESCAPED $mode"; exit 0; fi
echo "PQPRODUCER FAIL $mode observed real source mutant"; exit 1
