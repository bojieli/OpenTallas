#!/usr/bin/env bash
# H-NETLIST 0600: LG bank leaf RET_PIN=1 (one master, strap rret/wret) == parameter builds 10/7, 14/11, 18/15 every edge;
# strap-off-by-one mutant must fail for each. ONLY=1: mutant-only (exits nonzero when detected).
set -euo pipefail
cd "$(dirname "$0")/.."
out=$(realpath -m "${1:?out}"); mkdir -p "$out"; rc=0
for rw in "10 7" "14 11" "18 15"; do set -- $rw
  for m in ${ONLY:-0 1}; do
    iverilog -g2012 -s tb_lg_bank_ret_pin_eq -Ptb_lg_bank_ret_pin_eq.R=$1 -Ptb_lg_bank_ret_pin_eq.W=$2 -Ptb_lg_bank_ret_pin_eq.MUT=$m \
      -o "$out/r$1m$m.vvp" ot_hbm_vm_lg_static_bank.sv lg_ret_pin_0600/tb_lg_bank_ret_pin_eq.sv > "$out/b$1m$m.log" 2>&1
    set +e; vvp "$out/r$1m$m.vvp" > "$out/r$1m$m.log" 2>&1; r=$?; set -e
    grep LG_RET_PIN_EQ "$out/r$1m$m.log" | sed "s/^/MUT$m /"
    if [ $m = 0 ]; then [ $r = 0 ] || rc=1; else [ $r != 0 ] || { echo "MUT$m NOT DETECTED"; rc=1; }; fi
  done
done
if [ -n "${ONLY:-}" ]; then [ $rc = 0 ] && { echo "LG_RET_PIN_EQ FAIL (mutants detected)"; exit 1; }; exit 0; fi
[ $rc = 0 ] && echo "LG_RET_PIN_EQ GATE PASS" || { echo "LG_RET_PIN_EQ GATE FAIL"; exit 1; }
