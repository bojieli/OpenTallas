#!/usr/bin/env bash
# QW-N59-4 (10-19): lockstep benches of the hardened native59 split (qfd_native59_split_flat; -DN59_SPLIT_LP: its landed
# form qfd_native59_split_flat_lp) against the flat qfd_native59_dv_service_r1 (SAFE 2, EMB_RELAY 1, RST_FOREST 1), run by
# the two existing native59 programs (tb_qfd_native59_dv_service: NU 1 single user + embedding; tb_qfd_native59_dv_mu:
# NU 4 users, MCTX 1 overlapped ops) with the n59_split_shadow beside the reference DUT.  Verilator 5.050 (fleet).
# usage: run_native59_split_bench.sh OUTDIR      SPLIT_ONLY=<case> runs one case (closure-loop form; exit = the verdict)
#   pass cases : dv_positive dv_bad_q mu_positive mu_ovl_positive mu_ovl_ret_bad
#   mutants (the SPLIT carries the mutant, the reference is clean; must FAIL with N59(DV|MU)_FAIL):
#     m1_q_lane (Q lane packing) m2_kv_addr m3_emb_word m5_mu_tag (ovl) m7_owner (bank owner select)
#     qb1_unreg (bank q row unregistered: one edge early)  qb2_norelay (dd relay skipped; random stimulus)
#   random-stimulus lockstep (tb_n59_split_random): rnd_s1 rnd_s2 rnd_nu1 (pass), rnd_m1_q_lane rnd_qb1_unreg (must FAIL)
#   landed form (N59_SPLIT_LP=1, SPL_SOFF=6 SPL_BOFF=2 SPL_ROFF=6): + lp_m1_land_bypass lp_m2_land_late lp_rnd_m1_land_bypass
#     (lp.py MUT 1 / 2 inside the landed parent; must FAIL).  lp.py MUT 4 (the service reset run one stage long) is NOT a
#     mutant here: a reset-release offset is unobservable under the static calendar's idle window after reset (the split
#     itself releases its service one service-edge early for the same reason; see qfd_native59_qbank.sv).
#   SPL_SOFF / SPL_BOFF / SPL_ROFF (env): edge offsets (flat 1/0/1; the landed form: from its lp record)
set -uo pipefail
out=${1:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH
verilator --version
SO=${SPL_SOFF:-1};BO=${SPL_BOFF:-0};RO=${SPL_ROFF:-1}
COMMON=("$R/rtl/qwen_split/qfd_native59_qseat_sram.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v"
 "$R/rtl/qwen_split/qfd_native59_dv_service.sv"
 "$R/rtl/qwen_split/qfd_native59_qbank.sv" "$R/rtl/qwen_split/qfd_native59_svc.sv" "$R/rtl/qwen_split/qfd_native59_split_flat.sv"
 "$R/rtl/test/qwen_split/n59_split_shadow.sv"
 "$R/rtl/qwen_split/qfd_native59_q_export_control.sv" "$R/rtl/qwen_split/qfd_native59_command_context.sv"
 "$R/rtl/qwen_split/qfd_native59_static_service.sv" "$R/rtl/qwen_split/qfd_native59_record_endpoint.sv"
 "$R/rtl/qwen_split/qfd_kvn_static_transport.sv" "$R/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$R/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$R/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv")
if [[ -n ${N59_SPLIT_LP:-} ]]; then
 COMMON+=("$R/rtl/qwen_split/lp/qfd_native59_split_flat_lp.sv" "$R/rtl/common/landed_parent/ot_pl_land.sv"
  "$R/rtl/common/landed_parent/ot_pl_land_field_copies.sv" "$R/rtl/common/landed_parent/ot_pl_land_reset_forest.sv")
fi
DV=("$R/rtl/test/qwen_split/tb_qfd_native59_dv_service.sv" "$R/rtl/qwen_split/qfd_native59_compute_service.sv"
 "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv"
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
MU=("$R/rtl/test/qwen_split/tb_qfd_native59_dv_mu.sv")
RND=("$R/rtl/test/qwen_split/tb_n59_split_random.sv")
rc_all=0
run() { # name expect(pass|fail) tb(dv|mu) -G...
  local n=$1 exp=$2 tb=$3; shift 3
  [[ -n ${SPLIT_ONLY:-} && $n != "$SPLIT_ONLY" ]] && return
  local top src main tag
  if [[ $tb == dv ]]; then top=tb_qfd_native59_dv_service; src=("${DV[@]}"); tag=N59DV
  elif [[ $tb == rnd ]]; then top=tb_n59_split_random; src=("${RND[@]}"); tag=N59RND
  else top=tb_qfd_native59_dv_mu; src=("${MU[@]}"); tag=N59MU; fi
  main="$R/rtl/test/qwen_split/${top}_main.cpp"
  verilator --cc --exe --build -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module $top -GSAFE=2 -GEMBR=1 -DN59_R1 -DN59_SPLIT \
    ${N59_SPLIT_LP:+-DN59_SPLIT_LP} -GSPL_SOFF=$SO -GSPL_BOFF=$BO -GSPL_ROFF=$RO "$@" \
    -Mdir "$out/$n.obj" "${COMMON[@]}" "${src[@]}" "$main" > "$out/$n.build.log" 2>&1 \
    || { echo "$n BUILD_FAILED"; tail -30 "$out/$n.build.log"; rc_all=1; return; }
  "$out/$n.obj/V$top" > "$out/$n.log" 2>&1; local rc=$?
  local passed=0
  if [[ $tb == rnd ]]; then [[ $rc == 0 ]] && grep -q "^N59RND_PASS" "$out/$n.log" && passed=1
  else [[ $rc == 0 ]] && grep -q "^${tag}_PASS_SPLIT" "$out/$n.log" && grep -q "^${tag}_PASS" "$out/$n.log" && passed=1; fi
  if [[ $exp == pass ]]; then
    if [[ $passed == 1 ]]; then echo "$n OK (pass)"; else echo "$n UNEXPECTED FAIL rc=$rc"; rc_all=1; fi
  else
    if [[ $passed == 0 ]]; then echo "$n OK (mutant fails)"; else echo "$n MUTANT SURVIVED"; rc_all=1; fi
  fi
  grep -E "^(N59SPLIT_ERR|${tag}_ERR)" "$out/$n.log" | head -4
  grep -E "^${tag}( activity|_PASS|_FAIL)" "$out/$n.log" | tail -3 || echo "${tag}_NOVERDICT (sim rc=$rc)"
  [[ $passed == 0 ]] && echo "N59SPLIT_FAIL $n"
  if [[ -n ${SPLIT_ONLY:-} ]]; then rc_all=$((1-passed)); fi
  rm -rf "$out/$n.obj"
}
run dv_positive pass dv
run dv_bad_q pass dv -GBAD_Q=1
run mu_positive pass mu
run mu_ovl_positive pass mu -GOVLP=1 -GMCTX=1
run mu_ovl_ret_bad pass mu -GOVLP=1 -GMCTX=1 -GRET_BAD=1
run m1_q_lane fail mu -GOVLP=1 -GMCTX=1 -GSPLIT_MUT=1
run m2_kv_addr fail mu -GOVLP=1 -GMCTX=1 -GSPLIT_MUT=2
run m3_emb_word fail dv -GSPLIT_MUT=3
run m5_mu_tag fail mu -GOVLP=1 -GMCTX=1 -GSPLIT_MUT=5
run m7_owner fail dv -GSPLIT_MUT=7
run qb1_unreg fail mu -GOVLP=1 -GMCTX=1 -GQB_MUT=1
run qb2_norelay fail rnd -GQB_MUT=2
# random-stimulus lockstep (tb_n59_split_random): production NU 4 / MCTX 1 (2 seeds) and the NU 1 single-context block
run rnd_s1 pass rnd -GSEED=1
run rnd_s2 pass rnd -GSEED=2
run rnd_nu1 pass rnd -GSEED=3 -GNU=1 -GMCTX=0
run rnd_m1_q_lane fail rnd -GSPLIT_MUT=1
run rnd_qb1_unreg fail rnd -GQB_MUT=1
# landed form only (N59_SPLIT_LP=1): the lp.py landing mutants on the directed, fault-free MU programme
if [[ -n ${N59_SPLIT_LP:-} ]]; then
 run lp_m1_land_bypass fail mu -GOVLP=1 -GMCTX=1 -GLP_MUT=1
 run lp_m2_land_late fail mu -GOVLP=1 -GMCTX=1 -GLP_MUT=2
 run lp_rnd_m1_land_bypass fail rnd -GLP_MUT=1
fi
sha256sum "${COMMON[@]}" "${DV[@]}" "${MU[@]}" "${RND[@]}" > "$out/source.sha256"
echo "N59SPLIT_BENCH_EXIT $rc_all"; exit $rc_all
