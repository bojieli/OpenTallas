#!/bin/bash
# HC-XRDU 2026-10-18 (RELEASE_TREE H.STA.WIRE.8): LANDED-die bench of the HC ROOT ot_hbm_hc_root_static in the d4g U-ring
# form (hub DRLY 2, U relay XRLY 1, QDRLY 2) with the root <-> quarter die links at their COMPILED per-quarter latency
# (tools/hbm_die_v16/d4g_hc_xr.py on the landed contract; tb_hbm_hc_eng4_static HC_DIE_XRDQ/XRUQ register stages per
# quarter) and the root told XRD/XRU/XRDQ/XRUQ.  Lockstep with the single-block golden (tools/rtl_hbm_hc_eng_static_gate.py
# --split --rs 104, P1); the compiler constants follow the root: ingest lead DING = 2 + XRD, RAW0 = 167 + XRD + XRU.
# Usage: run_hbm_hc_root_landed.sh OUT MUT XRD XRU XRDQ XRUQ DIE_XRDQ DIE_XRUQ [DING [RAW0]]   (Q values bare hex XXXXXXXX)
#   pass (land smoke, d4g_hc_xr: XRD SW/SE/NW/NE 11/6/11/6, XRU 11/7/10/5):
#     MUT 0 XRD 11 XRU 11 XRDQ 060b060b XRUQ 050a070b DIE same          -> HC_ENG PASS
#   mutants: root unlanded (XRD = XRU = 0, all-1 Q, DING 2 RAW0 167) on the landed die -> HC_ENG_FAULT / FAIL
#            XRUQ SE 6 (die 7)  -> HC_ENG_FAULT ps=1      XRDQ NE 7 (die 6) -> HC_ENG_FAULT / FAIL
# Every verdict line is printed (no head cut).  Verilator 5.050 --hierarchical, ~50 GB RSS, ~25 min build.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:?MUT}; xrd=${3:?XRD}; xru=${4:?XRU}; xrdq=${5:?XRDQ}; xruq=${6:?XRUQ}
dxd=${7:?DIE_XRDQ}; dxu=${8:?DIE_XRUQ}; ding=${9:-$((2 + xrd))}; raw0=${10:-$((167 + xrd + xru))}; mkdir -p "$out"
# Q values: bare 8-digit hex (060b060b, the form closure-daemon specs must use: an unquoted 32'h... in a spec cmd pairs
# its apostrophes across arguments and shifts DIE_XRDQ/DIE_XRUQ away -- job hbm_hc_root_d4g_xr-r1 rc=1), or 32'hXXXXXXXX / 0xXXXXXXXX.
qv() { local v=${1#32\'h}; v=${v#0x}; [[ $v =~ ^[0-9a-fA-F]{8}$ ]] || { echo "bad Q value '$1' (want 8 hex digits)" >&2; exit 2; }; echo "32'h$v"; }
xrdq=$(qv "$xrdq"); xruq=$(qv "$xruq"); dxd=$(qv "$dxd"); dxu=$(qv "$dxu")
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version
H=rtl/hbm_accel/generic/peers/static_hc
src=(rtl/test/tb_hbm_hc_eng4_static.sv $H/ot_hbm_hc_root_static.sv $H/ot_hbm_hc_qeng_static.sv $H/ot_hbm_hc_qcen_static.sv
 $H/ot_hbm_hc_bankq_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_bank_static.sv $H/ot_hbm_hc_tail_unit_static.sv
 $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv $H/ot_hbm_hc_xw_rx_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv
 rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
python3 tools/rtl_hbm_hc_eng_static_gate.py --run "$out/case" --split --npos 1 --raw0 "$raw0" --rs 104 --ding "$ding" > "$out/vectors.log"
"$vl" --binary --timing --hierarchical -j "${HC_BUILD_JOBS:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --top-module tb_hbm_hc_eng4_static +define+MUT=$mut +define+OT_FP_DATA_NORST \
  +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_SAFE=${HC_SAFE:-0} +define+HC_CPR=${HC_CPR:-0} +define+HC_QDRLY=2 +define+HC_XRD=$xrd +define+HC_XRU=$xru \
  "+define+HC_XRDQ=$xrdq" "+define+HC_XRUQ=$xruq" "+define+HC_DIE_XRDQ=$dxd" "+define+HC_DIE_XRUQ=$dxu" -Mdir "$out/obj" -o Vroot \
  rtl/test/tb_hbm_hc_eng4_static_hier.vlt "${src[@]}" > "$out/build.log" 2>&1
set +e; (cd "$out/case" && "$out/obj/Vroot" $(cat plus.txt)) > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "HC_ENG_DONE|HC_ENG PASS|HC_ENG FAIL|HC_ENG_FAULT|MISMATCH" "$out/run.log" || true
echo "HC_ROOT_LANDED SAFE=${HC_SAFE:-0} CPR=${HC_CPR:-0} MUT=$mut XRD=$xrd XRU=$xru XRDQ=$xrdq XRUQ=$xruq DIE_XRDQ=$dxd DIE_XRUQ=$dxu DING=$ding RAW0=$raw0 rc=$rc"
rm -rf "$out/obj"
exit $rc
