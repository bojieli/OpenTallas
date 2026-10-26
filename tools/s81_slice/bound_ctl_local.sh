#!/bin/bash
# Current atomic RSTOP and XRT local timing; no die transport stages are assumed.
set -euo pipefail
O=$1
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/bin/verilator
for ring in ot_s81sl_rstop ot_s81sl_rstopt_xo; do
 for hb in 0 1; do
  id=${ring}_${hb}
  "$V" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -GHB=$hb +define+OT_RING_MASTER=$ring \
   --top-module tb_bound_ctl_local -Mdir "$O/obj_$id" --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' \
   rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/$ring.sv \
   rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/slice/test/tb_bound_ctl_local.sv > "$O/build_$id.log" 2>&1
  "$O/obj_$id/Vtb_bound_ctl_local" > "$O/run_$id.log" 2>&1
  grep '^BOUND_LOCAL\|^PASS\|^FAIL\|LOCAL_BAD' "$O/run_$id.log"
  grep -q '^PASS' "$O/run_$id.log"
  "$O/obj_$id/Vtb_bound_ctl_local" +age=6 > "$O/age_mut_$id.log" 2>&1
  grep -q '^FAIL' "$O/age_mut_$id.log"
 done
done
sha256sum rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/{ot_s81sl_rstop,ot_s81sl_rstopt_xo,ot_s81sl_xrt}.sv > "$O/sources.sha256"
echo 'BOUND_LOCAL_ALL_PASS wrong_age_mutants_caught'
