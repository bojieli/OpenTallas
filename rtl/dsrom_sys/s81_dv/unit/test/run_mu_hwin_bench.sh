#!/usr/bin/env bash
# MU-S81-2/DIE gate of dsdv_mu_hwin beside the CLOSED dsdv_mu_hslot (Verilator 5.050): base PASS, bad RX tag must fault,
# RTL mutants 3 (ab dropped) / 4 (replay enable ignored) must FAIL; plus the die-master lint (lint_lep_mu_die.sh).
# Usage: run_mu_hwin_bench.sh OUTDIR   (cwd anywhere; repo root = 5 levels up)
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:-$(mktemp -d)}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | tee "$O/verilator_version.txt"
U=$R/rtl/dsrom_sys/s81_dv/unit; F="$R/rtl/lib/ot_rst_relay.sv $R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $U/dsdv_mu_hslot.sv $U/dsdv_mu_mem.sv $R/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v $U/dsdv_mu_hwin.sv $U/test/tb_dsdv_mu_hwin.sv"
bad=0
run() { n=$1; shift
  verilator --binary --timing +define+DSDV_MU_POINTER_ASSERT +define+HEAD_COMPARE -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_dsdv_mu_hwin "$@" $F \
    --Mdir "$O/obj_$n" -o tb > "$O/build_$n.log" 2>&1 || { echo "BUILD_FAIL $n"; bad=1; return; }
  "$O/obj_$n/tb" > "$O/run_$n.log" 2>&1; grep -E '^MUWIN' "$O/run_$n.log" | sed "s/^/[$n] /"; }
run slots47 +define+NSLOT_TEST=47 +define+MIN_D=1; grep -q '^MUWIN PASS' "$O/run_slots47.log" || bad=1
run fast_cfg +define+FAST_CFG=1 +define+MIN_D=1; grep -q '^MUWIN PASS' "$O/run_fast_cfg.log" || bad=1
run min_d +define+MIN_D=1; grep -q '^MUWIN PASS' "$O/run_min_d.log" || bad=1
run badd +define+BAD_D=1; grep -q '^MUWIN BADD PASS' "$O/run_badd.log" || bad=1
run badd_high +define+BAD_D_HIGH=1; grep -q '^MUWIN BADD_HIGH PASS' "$O/run_badd_high.log" || bad=1
run base;  grep -q '^MUWIN PASS' "$O/run_base.log" || bad=1
run collision +define+COLLIDE_EVENTS=1; grep -q '^MUWIN COLLISION PASS' "$O/run_collision.log" || bad=1
run badrt +define+BADRT=1; grep -q 'BADRT PASS (fault raised)' "$O/run_badrt.log" || bad=1
for m in 3 4; do run mut$m +define+WMUT=$m
  if grep -q '^MUWIN PASS' "$O/run_mut$m.log"; then echo "mutant $m NOT detected"; bad=1; else echo "mutant $m detected (FAIL as required)"; fi
done
(cd "$R" && bash rtl/dsrom_sys/s81_dv/slice/test/lint_lep_mu_die.sh "$O/lint") || bad=1
[ $bad = 0 ] && echo "MU_HWIN_GATE PASS" || echo "MU_HWIN_GATE FAIL"; exit $bad
