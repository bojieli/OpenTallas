#!/usr/bin/env bash
set -euo pipefail
OUT=${1:?out};mkdir -p "$OUT";OUT=$(cd "$OUT" && pwd)
R=$PWD;W=rtl/qwen_sys/host_peer_mu_sram_1021p35/witnesses
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mapfile -t SRC < rtl/test/host_peer_main_fixture_1020/mu_sram/sources_p35.txt
CLEAN=()
for p in "${SRC[@]}"; do [[ "$p" == *_bb.v ]] || CLEAN+=("$p"); done
CLEAN+=(physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v)
run_case(){
 local case_name=$1 top=$2 flag=$3 ref=$4 tb=$5 expect=$6; local defs=(); if [[ "$flag" != none ]];then for f in $flag;do defs+=("-D$f");done;fi
 "$V" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "${defs[@]}" --top-module "$top" -Mdir "$OUT/obj_$case_name" "${CLEAN[@]}" "$W/$ref" "$W/$tb" >"$OUT/build_$case_name.log" 2>&1
 set +e
 "$OUT/obj_$case_name/V$top" >"$OUT/run_$case_name.log" 2>&1;rc=$?
 set -e
 if [[ "$expect" == pass ]];then [[ $rc == 0 ]];grep -Eq 'LCEQ PASS|RX_HEAD PASS' "$OUT/run_$case_name.log";else [[ $rc != 0 ]];grep -Eq 'LCEQ FAIL|P35_RX_META FAIL|RX_HEAD FAIL' "$OUT/run_$case_name.log";fi
 tail -4 "$OUT/run_$case_name.log"
}
run_case lc tb_lc_equiv none ref_lifecycle_p34.sv tb_lc_equiv.sv pass
run_case lc_stale tb_lc_equiv QKD_HR_PE_LHD_MUTANT ref_lifecycle_p34.sv tb_lc_equiv.sv fail
run_case rx tb_rx OT_PEER_RX_SRAM ref_packet_p34.sv tb_rx.sv pass
run_case rx_flags tb_rx 'OT_PEER_RX_SRAM QKD_PEER35_FLAGS_MUTANT' ref_packet_p34.sv tb_rx.sv fail
echo P35_SOURCE_PROOF_PASS
