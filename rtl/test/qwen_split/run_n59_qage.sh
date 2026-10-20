#!/usr/bin/env bash
# QW-N59-5 (10-20) Q.STA.N59.1: Q-ready age certificate of the hardened native59 split (tb_n59_qage.sv).
# usage: run_n59_qage.sh OUTDIR   (Verilator 5.050; env as the v5/v6 vehicle: N59_RECV=1 N59_QB_ALIGN=1 N59_QB_LOCAL32=1,
#        SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4).  One build, then the Q burst is swept toward the CMD (+QSHIFT) nominal and with
#        the +QLATE=1 timing mutant (Q dd words one edge late at the split = a 21-edge Q path).
# CERTIFICATE (N59QAGE_CERT_PASS): every nominal shift lockstep-PASSes (outputs incl. fault identical); the r1 reference
# has a boundary inside the sweep (largest fault-free shift SMAX, faulting at SMAX+1) -> the split keeps r1's exact Q
# write -> request / read age; the QLATE mutant FAILS lockstep at SMAX.  N59QAGE_MUTANT_ONLY=1: run only the mutant at the
# boundary found by a nominal sweep and exit 0 iff it FAILS (closure-loop mutant form, fail regex ^N59QAGE_LOCKSTEP_FAIL).
set -uo pipefail
out=${1:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH
verilator --version
SO=${SPL_SOFF:-3};BO=${SPL_BOFF:-0};RO=${SPL_ROFF:-4}
SRC=("$R/rtl/qwen_split/qfd_native59_qseat_sram.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v"
 "$R/rtl/qwen_split/qfd_native59_dv_service.sv"
 "$R/rtl/qwen_split/qfd_native59_qbank.sv" "$R/rtl/qwen_split/qfd_native59_svc.sv" "$R/rtl/qwen_split/qfd_native59_split_flat.sv"
 "$R/rtl/test/qwen_split/n59_split_shadow.sv"
 "$R/rtl/qwen_split/qfd_native59_q_export_control.sv" "$R/rtl/qwen_split/qfd_native59_command_context.sv"
 "$R/rtl/qwen_split/qfd_native59_static_service.sv" "$R/rtl/qwen_split/qfd_native59_record_endpoint.sv"
 "$R/rtl/qwen_split/qfd_kvn_static_transport.sv" "$R/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$R/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$R/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv"
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$R/rtl/test/qwen_split/tb_n59_qage.sv")
BDEFS=(-DN59_QB_LOCAL32=${N59_QB_LOCAL32:-1} -DN59_QB_LOCAL_MUT=${N59_QB_LOCAL_MUT:-0} -DN59_QB_ALIGN=${N59_QB_ALIGN:-1})
[[ ${N59_RECV:-1} == 1 ]] && BDEFS+=(-DN59_SVC_RECV -DN59_RECV_MUT=${N59_RECV_MUT:-0})
sha256sum "${SRC[@]}" "$R/rtl/test/qwen_split/tb_n59_qage_main.cpp" "$0" > "$out/source.sha256"
verilator --cc --exe --build -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_n59_qage -GSAFE=2 -GEMBR=1 -DN59_R1 -DN59_SPLIT \
  "${BDEFS[@]}" -GSPL_SOFF=$SO -GSPL_BOFF=$BO -GSPL_ROFF=$RO -Mdir "$out/obj" "${SRC[@]}" "$R/rtl/test/qwen_split/tb_n59_qage_main.cpp" \
  > "$out/build.log" 2>&1 || { echo "N59QAGE BUILD_FAILED"; tail -30 "$out/build.log"; exit 2; }
B="$out/obj/Vtb_n59_qage"
SHIFTS=${N59QAGE_SHIFTS:-"0 4 8 10 11 12 13 14 15 16 17 18 19 20 22 26 30"}
declare -A FLT LS
for s in $SHIFTS; do
 "$B" +QSHIFT=$s +QLATE=0 > "$out/nom_$s.log" 2>&1; rc=$?
 grep -E "^N59QAGE( r1|_LOCKSTEP)" "$out/nom_$s.log"
 f=$(sed -n 's/.* fault \(-\?[0-9]*\) done.*/\1/p' "$out/nom_$s.log" | head -1)
 FLT[$s]=${f:-X}; LS[$s]=$([[ $rc == 0 ]] && grep -q "^N59QAGE_LOCKSTEP_PASS" "$out/nom_$s.log" && echo P || echo F)
done
ok=1;smax=-1;prev=""
for s in $SHIFTS; do [[ ${LS[$s]} == P ]] || { echo "N59QAGE nominal lockstep FAIL at QSHIFT $s"; ok=0; }
 [[ ${FLT[$s]} == -1 ]] && smax=$s; done
nxt=""; for s in $SHIFTS; do (( s > smax )) && { nxt=$s; break; }; done
if (( smax < 0 )) || [[ -z $nxt ]] || [[ ${FLT[$nxt]} == -1 ]]; then echo "N59QAGE no r1 boundary inside the sweep (smax $smax next ${nxt:-none})"; ok=0; fi
# boundary must be exact: smax+1 must be in the sweep and fault
if [[ -n $nxt ]] && (( nxt != smax + 1 )); then echo "N59QAGE boundary not resolved to one edge (smax $smax next $nxt)"; ok=0; fi
age=$(sed -n 's/.*age_req_minus_lastq \(-\?[0-9]*\) .*/\1/p' "$out/nom_$smax.log" 2>/dev/null | head -1)
echo "N59QAGE r1 boundary: largest fault-free Q shift $smax (faults at $nxt); minimal internal age request - last Q dd word = $age edges"
mut_fail=0
for s in $smax 0; do
 "$B" +QSHIFT=$s +QLATE=1 > "$out/mut_$s.log" 2>&1; rc=$?
 grep -E "^N59QAGE( r1|_LOCKSTEP)" "$out/mut_$s.log"
 if [[ $s == $smax ]]; then { [[ $rc != 0 ]] && grep -q "^N59QAGE_LOCKSTEP_FAIL" "$out/mut_$s.log"; } && mut_fail=1; fi
done
rm -rf "$out/obj"
if [[ ${N59QAGE_MUTANT_ONLY:-0} == 1 ]]; then
 [[ $ok == 1 && $mut_fail == 1 ]] && { echo "N59QAGE_LOCKSTEP_FAIL (mutant QLATE rejected at boundary $smax)"; exit 1; }
 echo "N59QAGE_MUTANT_SURVIVED_OR_NO_BOUNDARY"; exit 0
fi
[[ $mut_fail == 1 ]] || { echo "N59QAGE QLATE mutant SURVIVED at the boundary $smax"; ok=0; }
if [[ $ok == 1 ]]; then
 echo "N59QAGE_CERT_PASS split keeps the r1 Q write->request/read age: boundary shift $smax, internal age $age edges, every shift lockstep PASS (SOFF $SO BOFF $BO ROFF $RO); QLATE (+1 edge Q path) rejected at the boundary"
 exit 0
fi
echo "N59QAGE_CERT_FAIL"; exit 1
