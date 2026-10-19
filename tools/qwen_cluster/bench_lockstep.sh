#!/bin/bash
# Q-CLUSTER16 lockstep bench (2026-10-18).  From the repo root (fleet host via ot-run):
#   tools/qwen_cluster/bench_lockstep.sh OUTDIR
# The 16-region fabric (rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv, one clock root per A0 tile) runs in lockstep with
# the 8-region fabric it replaces (rtl/test/qcluster_ref_8r_be7b9ff15.sv = the 0ed8da289 RTL, own *_r8 station masters):
# random inputs every cycle incl. two reset pulses, all outputs compared every cycle => same results AND same latency on
# every port (the 16-region split adds no edge).  MUT 0 at FAR 0 / 1 must PASS; fabric mutants MUT 1..5 and the station
# mutant S (rtl/test/qfd_c_stn_mut.sv: one inverted bit in qfd_c_stn516, DUT side only) must FAIL.
# Then the region audit (tools/qwen_cluster/region_audit.py: every register on its region's root, every seam crossing a
# single registered hop between neighbouring regions) must PASS, and its two mutants (station / tile clock rebound) FAIL.
# Q-CL16-LAND (10-18): the landed crossing leg_3_1b_0 (qfd_c_land.sv) adds E + 1 = 3 edges; the bench compares the ports it
# and its re-aligned sibling legs feed (n_a_1_2, n_b_1_2, n_a_0_0) against the reference delayed by exactly those edges
# (qc_gen.py port_added_edges), every cycle except the landed port while the landing is in reset / warm-up.  Landing
# mutants (must FAIL): MUT 6 = read slot K = E + 1, MUT 7 = read-side epoch one edge late (lockstep), and region-audit
# 'landclk' = the read half on the ring's write clock (a timing-only error, invisible to a one-clock RTL bench).
# Q-CLUSTER-LANDALL (10-18): EVERY multi-bit crossing is landed (54); each port is compared against the reference delayed
# by its documented offset (qc_gen.py: tap rows / bco / rs / rs_o / n_a / n_b, die_clock_contract.json
# compiler.port_added_edges); ports fed through landings are masked only around the bench's reset pulses (landing
# bubbles, contract L3).  MUT 6 / 7 act on landing leg_3_1b_1; region-audit 'unland' bypasses one landing (R6 FAIL).
# (The Q-CLUSTER3 soft reference qcluster_ref_c392aa534.sv differs by design since Q-CLUSTER4: rs_i->rs_o 16->17, reset 18->19.)
# Q-CB16RST (10-19): 16 die-delivered regional resets rst_<q> (all driven by the bench's rst_n = the die's equal-calendar
# release); MUT 8 = region c1r2's reset one edge late (die calendar slip, must FAIL); region-audit 'rsthop' feeds c1r2's
# reset pin register from c1r1's (a plain 1-bit seam crossing, R7 FAIL).
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-verilator}
COMMON=(rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv rtl/test/qcluster_ref_8r_be7b9ff15.sv
        rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv
        rtl/test/tb_qcluster_lockstep.sv)
{ sha256sum rtl/physical/qcluster/qfd_c_stn.sv rtl/test/qfd_c_stn_mut.sv "${COMMON[@]}" rtl/physical/qcluster/qfd_c_b16_dv.sv \
    tools/qwen_cluster/region_audit.py results/arch/qwen_cluster_1017/cluster_contract_dv.json "$0"; "$V" --version; } > "$OUT/sources.sha256"
rc=0
for MUT in 0 1 2 3 4 5 6 7 8 S; do
  if [[ $MUT == S ]]; then STN=rtl/test/qfd_c_stn_mut.sv; G=0; else STN=rtl/physical/qcluster/qfd_c_stn.sv; G=$MUT; fi
  "$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
     --top-module tb -GMUT=$G -Mdir "$OUT/obj$MUT" "$STN" "${COMMON[@]}" > "$OUT/build_$MUT.log" 2>&1 || { echo "BUILD_FAIL MUT $MUT"; rc=1; continue; }
  if [[ $MUT == 0 ]]; then FARS="0 1"; else FARS="0"; fi
  for FAR in $FARS; do
    ARG=""; [[ $FAR == 1 ]] && ARG="+FAR"
    (cd "$OUT" && ./obj$MUT/Vtb $ARG) > "$OUT/run_m${MUT}_f${FAR}.log" 2>&1
    if grep -q '^LOCKSTEP_PASS ' "$OUT/run_m${MUT}_f${FAR}.log" && ! grep -q '%Error\|%Fatal' "$OUT/run_m${MUT}_f${FAR}.log"; then
      v=PASS; else v=FAIL; fi
    if [[ $MUT == 0 ]]; then want=PASS; else want=FAIL; fi
    echo "RESULT MUT $MUT FAR $FAR: $v (expected $want) $(grep -h '^LOCKSTEP_' "$OUT/run_m${MUT}_f${FAR}.log")"
    [[ $v == "$want" ]] || rc=1
  done
  rm -rf "$OUT/obj$MUT"
done
for M in none station tile landclk unland rsthop; do
  if [[ $M == none ]]; then A=(); want=PASS; else A=(--mutate $M); want=FAIL; fi
  python3 tools/qwen_cluster/region_audit.py "${A[@]}" --out "$OUT/region_audit_$M.json" > "$OUT/region_audit_$M.log" 2>&1
  if grep -q '^REGION_AUDIT_PASS' "$OUT/region_audit_$M.log"; then v=PASS; else v=FAIL; fi
  echo "RESULT REGION_AUDIT $M: $v (expected $want) $(tail -n 1 "$OUT/region_audit_$M.log")"
  [[ $v == "$want" ]] || rc=1
done
echo "LOCKSTEP_EXIT $rc"
exit $rc
