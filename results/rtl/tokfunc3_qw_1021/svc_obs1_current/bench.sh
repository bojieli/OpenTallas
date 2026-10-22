#!/bin/bash
# SQ-C2-N59 (10-21): behavioural bench of qfd_native59_svc_obs1 at the kit parameters (tb_n59_svc_obs1_hp: lockstep vs the
# legacy qfd_native59_svc + independent head-prepare descriptor scoreboard).  usage: bench.sh CASE OUTDIR
#   pass: s1 s2 (random seeds)   mutants (private copy of the obs1 source, one text edit; must FAIL): m_hpseq m_hpdrop m_ret m_hosttag
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
case_=${1:?case}; run=${2:?outdir}; mkdir -p "$run"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
OBS=rtl/qwen_split/qfd_native59_svc_obs1.sv
SRCS=(rtl/qwen_split/qfd_native59_svc.sv rtl/qwen_split/qfd_native59_static_service.sv rtl/qwen_split/qfd_native59_static_service_obs1.sv
 rtl/qwen_split/mu/qfd_status_obs_hold_chunk.sv rtl/qwen_split/qfd_native59_mctx_helpers.sv rtl/qwen_split/qfd_native59_command_context.sv
 rtl/qwen_split/qfd_native59_q_export_control.sv rtl/qwen_split/qfd_native59_record_endpoint.sv rtl/qwen_split/qfd_kvn_static_transport.sv
 rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv
 rtl/test/qwen_split/tb_n59_svc_obs1_hp.sv)
seed=1; old=""; new=""; expect=pass
case "$case_" in
 s1) seed=1;; s2) seed=2;;
 m_hpseq) expect=fail; old="wire[13:0]hp_seq=fstart[hp_u1]?fseq[hp_u1]+14'd1:fseq[hp_u1];"; new="wire[13:0]hp_seq=fstart[hp_u1]?fseq[hp_u1]+14'd2:fseq[hp_u1];";;
 m_hpdrop) expect=fail; old="hp_v<={hp_v[0],head_prepare_v};"; new="hp_v<={hp_v[0],head_prepare_v&&head_prepare_user!=2'd2};";;
 m_ret) expect=fail; old="else native_ret<=service_ret_raw;"; new="else native_ret<=service_ret_raw^{94'd0,p_cs};";;
 m_hosttag) expect=fail; old="head_descriptor_tag<={p_ht[58:43],6'd0,p_ht[36:0]};"; new="head_descriptor_tag<={p_ht[58:43],6'd1,p_ht[36:0]};";;
 *) echo "N59OBS_BENCH unknown case $case_"; exit 2;;
esac
obs="$root/$OBS"
if [ -n "$old" ]; then
  obs="$run/mut_$(basename $OBS)"
  python3 - "$root/$OBS" "$obs" "$old" "$new" <<'PY' || { echo "N59OBS_BENCH mutation source mismatch"; exit 2; }
import sys
s=open(sys.argv[1]).read()
assert s.count(sys.argv[3])==1, 'mutation anchor count != 1'
open(sys.argv[2],'w').write(s.replace(sys.argv[3],sys.argv[4]))
PY
fi
abs=(); for f in "${SRCS[@]}"; do abs+=("$root/$f"); done
"$VL" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_n59_svc_obs1_hp \
  -GSEED=$seed -Mdir "$run/obj" "$obs" "${abs[@]}" > "$run/build.log" 2>&1 || { echo "N59OBS_BENCH build failed"; tail -20 "$run/build.log"; exit 3; }
"$run/obj/Vtb_n59_svc_obs1_hp" > "$run/sim.log" 2>&1; rc=$?
cat "$run/sim.log" | grep -E '^N59OBS' | head -12
sha256sum "$obs" "${abs[@]}" > "$run/source.sha256"
sha256sum "$run/obj/Vtb_n59_svc_obs1_hp" > "$run/binary.sha256"
if grep -q '^N59OBS_PASS' "$run/sim.log" && [ $rc = 0 ]; then echo "N59OBS_CASE $case_ PASS"; [ $expect = pass ] && exit 0 || { echo "N59OBS_MUTANT_SURVIVED $case_"; exit 0; }
else echo "N59OBS_CASE $case_ FAIL"; [ $expect = fail ] && { echo "N59OBS_MUTANT_REJECTED $case_"; exit 1; } || exit 1; fi
