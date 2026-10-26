#!/bin/bash
# HBM-B-RTL2b (2026-10-17): HC quarter engine RING form lockstep -- tb_hbm_hc_eng4_static (root TPRE=6 + 4 x
# ot_hbm_hc_qeng_static = hub centre ot_hbm_hc_qcen_static + 8 ring bank tiles ot_hbm_hc_bankq*_static) against the
# single-block golden (tools/rtl_hbm_hc_eng_static_gate.py --split, P1, RAW0 165 / RS 104 from the split probe).
# Usage: [HC_CPR=0|1] run_hbm_hc_eng4_ring.sh OUT [MUT]   (MUT 0: HC_ENG PASS, HC_MIX_CYCLES 996; MUT 1 bank-3 corner rotation /
# 3 x landing / 4 tree order: HC_ENG FAIL).  Verilator 5.050 --hierarchical, ~50 GB RSS, ~25 min build.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
src=(rtl/test/tb_hbm_hc_eng4_static.sv $H/ot_hbm_hc_root_static.sv $H/ot_hbm_hc_qeng_static.sv $H/ot_hbm_hc_qcen_static.sv
 $H/ot_hbm_hc_bankq_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_bank_static.sv $H/ot_hbm_hc_tail_unit_static.sv
 $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv $H/ot_hbm_hc_xw_rx_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
# HBM-HCBANK6 10-20: HC_XDEF containing +define+HC_BANK_RC builds the ring from the regional-clock bank successors
# (ot_hbm_hc_bankrc_static.sv, hier block ot_hbm_hc_bankrc_core); otherwise byte-identical.
vlt=rtl/test/tb_hbm_hc_eng4_static_hier.vlt
if [[ "${HC_XDEF:-}" == *HC_BANK_RC* ]]; then src+=($H/ot_hbm_hc_bankrc_static.sv); vlt=rtl/test/tb_hbm_hc_eng4_static_hier_rc.vlt; fi
# HC-RINGPLAN 10-19: HC_XDEF = extra verilator defines (e.g. the GEN2d closed ring "+define+HC_DRLY=2 +define+HC_XRLY=0":
# bank 0 DRLY 2, no b7->b0 relay, hub/root DRLY 2); unset = byte-identical build.
# HH-9 10-19: HC_CPR (default 1 = the adopted ring: bank chain pin registers, chain +11 edges -> RAW0 165 + 11)
cpr=${HC_CPR:-1}
# HC-RINGPLAN2 10-19: the programme RAW0 follows the DESIGN quarter relay depth HC_DRLY (from HC_XDEF, default 1): each
# DRLY register beyond 1 delays the raw return by 2 edges (centre desc relay + bank 0 exit relay; root SYS_LAT0 2*QDRLY;
# HBM-RTL5 u0: DRLY 2 -> RAW0 165 -> 167). HC_QDRLY in HC_XDEF is a root mutant and does NOT move RAW0. HC_RAW0 overrides.
drly=$(sed -n 's/.*+define+HC_DRLY=\([0-9][0-9]*\).*/\1/p' <<<"${HC_XDEF:-}"); drly=${drly:-1}
raw0=${HC_RAW0:-$((165 + 11 * cpr + 2 * (drly - 1)))}
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case" --split --npos 1 --raw0 $raw0 --rs 104 --ding 12 > "$out/vectors.log"
# HCRING 10-19: HC_JOINT_MAP=<dir with hc_joint_map.svh> wires the 8 ring links as the bank tile faces abut
# (tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py --svh); unset = name-wired (unchanged).
jm=(); jtag=names
if [ -n "${HC_JOINT_MAP:-}" ]; then jdir=$(realpath "$HC_JOINT_MAP"); [ -f "$jdir/hc_joint_map.svh" ] || { echo "no $jdir/hc_joint_map.svh"; exit 2; }
  jm=(+define+OT_HC_JOINT_MAP +incdir+"$jdir"); jtag=$(head -1 "$jdir/hc_joint_map.svh" | tr -d '/'); fi
"$vl" --binary --timing --hierarchical -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --top-module tb_hbm_hc_eng4_static +define+MUT=$mut +define+HC_CPR=$cpr +define+OT_FP_DATA_NORST "${jm[@]}" ${HC_XDEF:-} -Mdir "$out/obj" -o Vring \
  "$vlt" "${src[@]}" > "$out/build.log" 2>&1
set +e; (cd "$out/case" && "$out/obj/Vring" $(cat plus.txt)) > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "HC_ENG_DONE|HC_ENG PASS|HC_ENG FAIL|FAULT" "$out/run.log" | head -4
echo "HC_RING_LOCKSTEP MUT=$mut rc=$rc (CPR=$cpr RAW0=$raw0${HC_XDEF:+ XDEF=$HC_XDEF})"
echo "HC_RING_JOINTS $jtag"

if [ "$rc" != 0 ]; then exit "$rc"; fi
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case_bad_ding" --split --npos 1 --raw0 $raw0 --rs 104 --ding 2 > "$out/vectors_bad.log"
set +e
(cd "$out/case_bad_ding" && "$out/obj/Vring" $(cat plus.txt)) > "$out/run_bad_ding.log" 2>&1
neg=$?
set -e
[ "$neg" != 0 ] || { echo HC_R8_MUTANT_NOT_CAUGHT; exit 1; }
echo "HC_R8_EXACT PASS XRD10_XRU10 RAW0=$raw0 DING12 wrongDING2_CAUGHT_rc=$neg extra_unit_cycles=20"

