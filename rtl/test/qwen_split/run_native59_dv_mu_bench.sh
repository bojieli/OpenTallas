#!/usr/bin/env bash
# MU-DQ-D2DUSER (10-19): the compute die's D2D attention user tag (qfd_native59_dv_service NU 4) under Verilator 5.050
# (the closure daemon's; FLEET only).  usage: run_native59_dv_mu_bench.sh OUTDIR
#   positive        4 users, 14 ops: every CMD / Q beat tagged {seq14, user}, returns matched, user 0 == NU 1  -> N59MU_PASS
#   ret_bad         the KV side answers user 2 with user tag 1: the service must fault, no completion      -> N59MU_PASS
#   mut5_m7         user 3's CMD / Q carry user tag 0 (MU-TOK-KV m7 at the compute end)                  -> must FAIL
#   mut6_seq        the filler epoch sequence never advances                                             -> must FAIL
#   regress_nu1     the as-built NU 1 bench (run_native59_dv_service_bench.sh: positive, bad_q, mut1-3) -> rc 0
#   mctx_serial / ovl_positive / ovl_ret_bad (pass), ovl_asbuilt_1ctx / ovl_mut_collide / ovl_mut5_m7 (must FAIL): MU-D2D-OVL
#   overlapped operations on the two-context service (MCTX 1); see the bench header.
#   N59MU_ONLY=<name> runs one case (closure-loop form).
set -uo pipefail
out=${1:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH
verilator --version
SRC=("$R/rtl/test/qwen_split/tb_qfd_native59_dv_mu.sv"
 "$R/rtl/qwen_split/qfd_native59_dv_service.sv"
 "$R/rtl/qwen_split/qfd_native59_q_export_control.sv" "$R/rtl/qwen_split/qfd_native59_command_context.sv"
 "$R/rtl/qwen_split/qfd_native59_static_service.sv" "$R/rtl/qwen_split/qfd_native59_record_endpoint.sv"
 "$R/rtl/qwen_split/qfd_kvn_static_transport.sv" "$R/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$R/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$R/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv")
rc_all=0
run() { # name expect(pass|fail) -G...
  local n=$1 exp=$2; shift 2
  [[ -n ${N59MU_ONLY:-} && $n != "$N59MU_ONLY" ]] && return
  verilator --cc --exe --build -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qfd_native59_dv_mu "$@" \
    -Mdir "$out/$n.obj" "${SRC[@]}" "$R/rtl/test/qwen_split/tb_qfd_native59_dv_mu_main.cpp" > "$out/$n.build.log" 2>&1 \
    || { echo "$n BUILD_FAILED"; tail -20 "$out/$n.build.log"; rc_all=1; return; }
  "$out/$n.obj/Vtb_qfd_native59_dv_mu" > "$out/$n.log" 2>&1; local rc=$?
  if [[ $exp == pass ]]; then
    if [[ $rc == 0 ]] && grep -q '^N59MU_PASS' "$out/$n.log"; then echo "$n OK (pass)"; else echo "$n UNEXPECTED FAIL rc=$rc"; rc_all=1; fi
  else
    if [[ $rc != 0 ]] || ! grep -q '^N59MU_PASS' "$out/$n.log"; then echo "$n OK (mutant fails)"; echo "N59MU_FAIL $n"; else echo "$n MUTANT SURVIVED"; rc_all=1; fi
  fi
  grep -E '^N59MU_' "$out/$n.log" | head -4
  # MU-D2D-OVL (closure daemon form, as QW-N59's dv_service wrapper): the simulator's verdict line on stdout, and in
  # N59MU_ONLY mode the exit code is the simulator's raw verdict (0 only on N59MU_PASS; a mutant run exits non-zero)
  grep -E '^N59MU_(PASS|FAIL)' "$out/$n.log" | tail -1 || echo "N59MU_NOVERDICT (sim rc=$rc)"
  if [[ -n ${N59MU_ONLY:-} ]]; then
    if [[ $rc == 0 ]] && grep -q '^N59MU_PASS' "$out/$n.log"; then rc_all=0; else rc_all=1; fi
  fi
  rm -rf "$out/$n.obj"
}
run positive pass
run ret_bad pass -GRET_BAD=1
run mut5_m7 fail -GMUT=5
run mut6_seq fail -GMUT=6
# MU-D2D-OVL 10-19: overlapped operations (op k+1's front while op k's back is in flight), two context slots (MCTX 1)
run mctx_serial pass -GMCTX=1
run ovl_positive pass -GOVLP=1 -GMCTX=1
run ovl_ret_bad pass -GOVLP=1 -GMCTX=1 -GRET_BAD=1
run ovl_asbuilt_1ctx fail -GOVLP=1 -GMCTX=0
run ovl_mut_collide fail -GOVLP=1 -GMCTX=1 -GCOLL=1
run ovl_mut5_m7 fail -GOVLP=1 -GMCTX=1 -GMUT=5
if [[ -z ${N59MU_ONLY:-} || ${N59MU_ONLY:-} == regress_nu1 ]]; then
  VERILATOR=$VL bash "$R/rtl/test/qwen_split/run_native59_dv_service_bench.sh" "$out/regress_nu1" > "$out/regress_nu1.log" 2>&1 \
    && echo "regress_nu1 OK" || { echo "regress_nu1 FAIL"; rc_all=1; }
  cat "$out/regress_nu1.log"
fi
sha256sum "${SRC[@]}" > "$out/source.sha256"
echo "N59MU_BENCH_EXIT $rc_all"; exit $rc_all
