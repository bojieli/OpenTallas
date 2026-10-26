#!/usr/bin/env bash
# H-NETLIST/su 2026-10-15 benches: (1) ot_hbm_su_bridge_release vs the ideal phase-zero release on two real
# ot_hbm_su_multirate_bridge instances (positive, 4 runs; misaligned restart must FAULT; MUT1 early / MUT2 late must FAIL);
# (2) ot_hbm_su_static_qcore port moves (rf_drain_cmd, red_rf_v) equivalent to the pre-change core (positive; MUT16 /
# MUT32 must FAIL).  usage: run_su_netlist_joins.sh OUT     (iverilog -g2012; qcore bench ~10 min a build)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
BASE=4b43cd77c   # last commit with the composition ANDs (reference core)
git show $BASE:$S/top/ot_hbm_su_static_qcore.sv | sed 's/^module ot_hbm_su_static_qcore/module qcore_base/' > "$out/qcore_base.sv"
rc=0
br=($S/top/tb_hbm_su_bridge_release.sv $S/top/ot_hbm_su_bridge_release.sv $S/programme/multirate_bridge.sv)
for m in 0 1 2; do
  iverilog -g2012 -Ptb_hbm_su_bridge_release.MUT=$m -o "$out/br$m.vvp" "${br[@]}"
  if [ $m = 0 ]; then
    vvp -n "$out/br0.vvp" +RUNS=4 > "$out/bridge_pos.log" 2>&1 || rc=1
    set +e; vvp -n "$out/br0.vvp" +RUNS=3 +MISALIGN > "$out/bridge_misalign.log" 2>&1; r=$?; set -e
    grep -q "leaf_fault=1" "$out/bridge_misalign.log" && [ $r = 0 ] || { echo "misaligned restart not faulted"; rc=1; }
  else
    set +e; vvp -n "$out/br$m.vvp" > "$out/bridge_mut$m.log" 2>&1; r=$?; set -e
    [ $r != 0 ] && grep -q "BRIDGE_RELEASE FAIL" "$out/bridge_mut$m.log" || { echo "bridge MUT$m NOT KILLED"; rc=1; }
  fi
  rm -f "$out/br$m.vvp"
done
qc=($S/top/tb_hbm_su_qcore_ports.sv "$out/qcore_base.sv" $S/top/ot_hbm_su_static_qcore.sv $S/register_file/ot_hbm_su_static_rf.sv
    $S/reduction/ot_hbm_su_reduce_static.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
    rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
for m in 0 16 32; do
  iverilog -g2012 -Ptb_hbm_su_qcore_ports.MUT=$m -o "$out/q$m.vvp" "${qc[@]}" > "$out/qcore_build$m.log" 2>&1
  set +e; vvp -n "$out/q$m.vvp" > "$out/qcore_m$m.log" 2>&1; r=$?; set -e
  if [ $m = 0 ]; then [ $r = 0 ] && grep -q "QCORE_PORTS PASS" "$out/qcore_m0.log" || rc=1
  else [ $r != 0 ] && grep -q "QCORE_PORTS FAIL" "$out/qcore_m$m.log" || { echo "qcore MUT$m NOT KILLED"; rc=1; }; fi
  rm -f "$out/q$m.vvp"
done
grep -h "BRIDGE_RELEASE\|QCORE_PORTS" "$out"/bridge_*.log "$out"/qcore_m*.log
sha256sum "${br[@]}" "${qc[@]}" > "$out/sources.sha256"
[ $rc = 0 ] && echo "SU_NETLIST_JOINS GATE PASS" || { echo "SU_NETLIST_JOINS GATE FAIL"; exit 1; }
