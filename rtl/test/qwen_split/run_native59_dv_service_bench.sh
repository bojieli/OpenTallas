#!/usr/bin/env bash
# Q-N59 (10-17): qfd_native59_dv_service vs qfd_native59_compute_service equivalence bench under Verilator.
# usage: run_native59_dv_service_bench.sh OUTDIR
#   positive (MUT 0) must print N59DV_PASS; BAD_Q (one Q dd word never sent) must PASS its fault check;
#   mutants MUT 1 (Q lane packing), 2 (KV lane address), 3 (EMB code word index) must FAIL.
#   N59_ONLY=<run name> (S-QWCOL 10-18, closure-loop benches): run only that one (positive|bad_q|mut1_q_lane|...).
set -uo pipefail
out=${1:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../.." && pwd)
SRC=("$R/rtl/qwen_split/qfd_native59_qseat_sram.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v"
 "$R/rtl/test/qwen_split/tb_qfd_native59_dv_service.sv"
 "$R/rtl/qwen_split/qfd_native59_dv_service.sv" "$R/rtl/qwen_split/qfd_native59_compute_service.sv"
 "$R/rtl/qwen_split/qfd_native59_q_export_control.sv" "$R/rtl/qwen_split/qfd_native59_command_context.sv"
 "$R/rtl/qwen_split/qfd_native59_static_service.sv" "$R/rtl/qwen_split/qfd_native59_record_endpoint.sv"
 "$R/rtl/qwen_split/qfd_kvn_static_transport.sv" "$R/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$R/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$R/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv"
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
rc_all=0
run() { # name expect(pass|fail) -G...
  local n=$1 exp=$2; shift 2
  [[ -n ${N59_ONLY:-} && $n != "$N59_ONLY" ]] && return
  verilator --cc --exe --build -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qfd_native59_dv_service -GSAFE=${N59_SAFE:-0} "$@" \
    -Mdir "$out/$n.obj" "${SRC[@]}" "$R/rtl/test/qwen_split/tb_qfd_native59_dv_service_main.cpp" > "$out/$n.build.log" 2>&1 \
    || { echo "$n BUILD_FAILED"; tail -20 "$out/$n.build.log"; rc_all=1; return; }
  "$out/$n.obj/Vtb_qfd_native59_dv_service" > "$out/$n.log" 2>&1; local rc=$?
  if [[ $exp == pass ]]; then
    if [[ $rc == 0 ]] && grep -q '^N59DV_PASS' "$out/$n.log"; then echo "$n OK (pass)"; else echo "$n UNEXPECTED FAIL rc=$rc"; rc_all=1; fi
  else
    if [[ $rc != 0 ]] || ! grep -q '^N59DV_PASS' "$out/$n.log"; then echo "$n OK (mutant fails)"; else echo "$n MUTANT SURVIVED"; rc_all=1; fi
  fi
  grep -E '^N59DV_ERR' "$out/$n.log" | head -3
  # QW-N59 10-19: the simulator's own verdict line goes to stdout (the closure daemon judges fail_regex '^N59DV_FAIL'
  # on the stage log, which held only the first 3 ERR lines), and in N59_ONLY mode the exit code is the simulator's raw
  # verdict (non-zero = the run FAILED, the daemon's expect-fail convention); the all-runs mode keeps rc 0 = as expected.
  grep -E '^N59DV_(PASS|FAIL)' "$out/$n.log" || echo "N59DV_NOVERDICT (sim rc=$rc): not a detected mutant"
  if [[ -n ${N59_ONLY:-} ]]; then
    if [[ $rc == 0 ]] && grep -q '^N59DV_PASS' "$out/$n.log"; then rc_all=0; else rc_all=1; fi
  fi
  rm -rf "$out/$n.obj"
}
run positive pass
run bad_q pass -GBAD_Q=1
run mut1_q_lane fail -GMUT=1
run mut2_kv_addr fail -GMUT=2
run mut3_emb_word fail -GMUT=3
sha256sum "${SRC[@]}" > "$out/source.sha256"
exit $rc_all
