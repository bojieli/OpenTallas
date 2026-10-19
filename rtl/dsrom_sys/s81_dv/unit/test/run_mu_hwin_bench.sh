#!/usr/bin/env bash
# MU-S81-2/DIE gate of dsdv_mu_hwin beside the CLOSED dsdv_mu_hslot (Verilator 5.050): base PASS, bad RX tag must fault,
# RTL mutants 3 (ab dropped) / 4 (replay enable ignored) must FAIL; plus the die-master lint (lint_lep_mu_die.sh).
# Usage: run_mu_hwin_bench.sh OUTDIR   (cwd anywhere; repo root = 5 levels up)
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:-$(mktemp -d)}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | tee "$O/verilator_version.txt"
U=$R/rtl/dsrom_sys/s81_dv/unit; F="$R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_hslot.sv $U/dsdv_mu_hwin.sv $U/test/tb_dsdv_mu_hwin.sv"
bad=0
run() { n=$1; shift
  verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_dsdv_mu_hwin "$@" $F \
    --Mdir "$O/obj_$n" -o tb > "$O/build_$n.log" 2>&1 || { echo "BUILD_FAIL $n"; bad=1; return; }
  "$O/obj_$n/tb" > "$O/run_$n.log" 2>&1; grep -E '^MUWIN' "$O/run_$n.log" | sed "s/^/[$n] /"; }
run base;  grep -q '^MUWIN PASS' "$O/run_base.log" || bad=1
run badrt +define+BADRT=1; grep -q 'BADRT PASS (fault raised)' "$O/run_badrt.log" || bad=1
for m in 3 4; do run mut$m +define+WMUT=$m
  if grep -q '^MUWIN PASS' "$O/run_mut$m.log"; then echo "mutant $m NOT detected"; bad=1; else echo "mutant $m detected (FAIL as required)"; fi
done
(cd "$R" && bash rtl/dsrom_sys/s81_dv/slice/test/lint_lep_mu_die.sh "$O/lint") || bad=1
[ $bad = 0 ] && echo "MU_HWIN_GATE PASS" || echo "MU_HWIN_GATE FAIL"; exit $bad
