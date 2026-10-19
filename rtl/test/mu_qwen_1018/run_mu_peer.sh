#!/bin/bash
# MU-KV-PEER 10-19: the die-0 coordinator chain at MU 1 (token service / coordinator / codec / services / lifecycle /
# cohort / POST collector _mu) and the MU 1 qkd_hr_core_peer.  Verilator 5.050 (the closure daemon's version).
# usage: run_mu_peer.sh ROOT OUT CASE
#   MU 1 PASS : tb_mu_peer_e2e (4 users x 3 rounds pipelined through the whole chain + endpoint _mu + KV lprg _mu) |
#               tb_mu_peer_abort (same, then a package abort with 3 retained users: 1 terminated, 2 live) |
#               lint_peer_mu (the MU 1 qkd_hr_core_peer with its member sources)
#   MU 0 ident: ex_peer_lifecycle / ex_peer_lifecycle_mu0 (existing coordinator+8 rank bench; _mu0 binds every _mu at
#               MU 0: coordinator, codec, services, lifecycle, POST collector, allocator, cohort) |
#               ex_lifecycle / ex_lifecycle_mu0 (existing lifecycle bench; lifecycle, allocator, cohort _mu at MU 0) |
#               ex_tsvc / ex_tsvc_mu0 (existing 8-die token-service bench on the collected token service; _mu at MU 0)
#   mutants (must FAIL): ts1 ts2 co1 lc1 cd1 cd2 pc1 ep3 sv1 ab1
# Every file a case reads is in lists/<list>.f.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
M=rtl/qwen_sys/mu_qwen_20261018; HI=rtl/qwen_sys/host_integrated_20261014; RQ=rtl/qwen_sys/redesign_qwen
TS=$M/qkd_host_ctrl_token_service_packet_collected_mu.sv; CD=$M/qkd_host_peer_coordinator_codec_mu.sv
CO=$M/ot_qwen_tp8_token_cohort_mu.sv; LC=$M/qkd_host_lifecycle_collected_mu.sv; PC=$M/qkd_host_post_collector_mu.sv
EP=$M/qkd_host_native_token_endpoint_cancel_mu.sv; SV=$M/qkd_host_coordinator_services_mu.sv
TB=$CASE; LIST=$CASE; SUBS=""; PA="${MU_PEER_PA:-}"
sub(){ SUBS="$SUBS$1"$'\x1f'"$2"$'\x1f'"$3"$'\x1e'; }
case "$CASE" in
 tb_mu_peer_e2e|lint_peer_mu) ;;
 tb_mu_peer_abort) TB=tb_mu_peer_e2e; LIST=$TB; PA=+ABORT;;
 # lifecycle does not acknowledge a cancel of a user's already-terminated identity (abort case must then FAIL)
 ab1) TB=tb_mu_peer_e2e; LIST=$TB; PA=+ABORT; sub $LC '((pp[cu] || lt_v[cu]) && cancel_tag' '((pp[cu]) && cancel_tag';;
 ex_peer_lifecycle) TB=tb_qkd_host_peer_lifecycle; LIST=$TB;;
 ex_peer_lifecycle_mu0) TB=tb_qkd_host_peer_lifecycle; LIST=$TB
   sub rtl/test/qwen_host/tb_qkd_host_peer_lifecycle.sv ' qkd_host_tp8_coordinator d(' ' qkd_host_tp8_coordinator_mu #(.MU(0)) d('
   sub $HI/qkd_host_tp8_coordinator.sv ' qkd_host_peer_coordinator_codec u_peer(' ' qkd_host_peer_coordinator_codec_mu #(.MU(0)) u_peer('
   sub $HI/qkd_host_tp8_coordinator.sv ' qkd_host_coordinator_services u_lifecycle(' ' qkd_host_coordinator_services_mu #(.MU(0)) u_lifecycle('
   sub $HI/qkd_host_coordinator_services.sv 'qkd_host_lifecycle_collected #(.INITIAL_EPOCH(INITIAL_EPOCH))u_lifecycle(' 'qkd_host_lifecycle_collected_mu #(.INITIAL_EPOCH(INITIAL_EPOCH),.MU(0))u_lifecycle('
   sub $HI/qkd_host_coordinator_services.sv ' qkd_host_post_collector u_post(' ' qkd_host_post_collector_mu #(.MU(0)) u_post('
   sub $HI/qkd_host_lifecycle_collected.sv 'ot_qwen_tp8_token_epoch_allocator #(.INITIAL_EPOCH(INITIAL_EPOCH)) allocator' 'ot_qwen_tp8_token_epoch_allocator_mu #(.INITIAL_EPOCH(INITIAL_EPOCH),.MU(0)) allocator'
   sub $HI/qkd_host_lifecycle_collected.sv ' ot_qwen_tp8_token_cohort cohort (' ' ot_qwen_tp8_token_cohort_mu #(.MU(0)) cohort (';;
 ex_lifecycle) TB=tb_qkd_host_lifecycle_collected; LIST=tb_qkd_host_lifecycle_collected_peer;;
 ex_lifecycle_mu0) TB=tb_qkd_host_lifecycle_collected; LIST=tb_qkd_host_lifecycle_collected_peer
   sub rtl/test/qwen_host/tb_qkd_host_lifecycle_collected.sv 'qkd_host_lifecycle_collected #(.INITIAL_EPOCH(16'"'"'hffff)) dut' 'qkd_host_lifecycle_collected_mu #(.INITIAL_EPOCH(16'"'"'hffff),.MU(0)) dut'
   sub $HI/qkd_host_lifecycle_collected.sv 'ot_qwen_tp8_token_epoch_allocator #(.INITIAL_EPOCH(INITIAL_EPOCH)) allocator' 'ot_qwen_tp8_token_epoch_allocator_mu #(.INITIAL_EPOCH(INITIAL_EPOCH),.MU(0)) allocator'
   sub $HI/qkd_host_lifecycle_collected.sv ' ot_qwen_tp8_token_cohort cohort (' ' ot_qwen_tp8_token_cohort_mu #(.MU(0)) cohort (';;
 ex_tsvc) TB=tb_qkd_host_control_token_service; LIST=tb_qkd_host_control_token_service_peer
   sub rtl/test/qwen_host/tb_qkd_host_control_token_service.sv 'qkd_host_ctrl_token_service_packet #(' 'qkd_host_ctrl_token_service_packet_collected #('
   sub rtl/qwen_sys/host_20261013/qkd_host_packet_bundle_token_service.sv 'qkd_host_ctrl_token_service_packet #(' 'qkd_host_ctrl_token_service_packet_collected #(';;
 ex_tsvc_mu0) TB=tb_qkd_host_control_token_service; LIST=tb_qkd_host_control_token_service_peer
   sub rtl/test/qwen_host/tb_qkd_host_control_token_service.sv 'qkd_host_ctrl_token_service_packet #(' 'qkd_host_ctrl_token_service_packet_collected_mu #(.MU(0),'
   sub rtl/qwen_sys/host_20261013/qkd_host_packet_bundle_token_service.sv 'qkd_host_ctrl_token_service_packet #(' 'qkd_host_ctrl_token_service_packet_collected_mu #(.MU(0),'
   # the bench's drain probe names three u_ctrl registers: they now sit one wrapper level down (g_plain.u_plain)
   sub rtl/test/qwen_host/tb_qkd_host_control_token_service.sv '!dut.u_packet.u_ctrl.busy&&dut.u_packet.u_ctrl.cn==0&&!dut.u_packet.u_ctrl.cv&&' '!dut.u_packet.u_ctrl.g_plain.u_plain.busy&&dut.u_packet.u_ctrl.g_plain.u_plain.cn==0&&!dut.u_packet.u_ctrl.g_plain.u_plain.cv&&';;
 # token service keeps the single-user START position check (pos[17:13] == 0): users 1..3 fault at die 0
 ts1) TB=tb_mu_peer_e2e; LIST=$TB; sub $TS 'cq[cr][15:13]!=0' 'cq[cr][17:13]!=0';;
 # peers keep ONE global epoch freshness (epochs of interleaved users are not globally increasing)
 ts2) TB=tb_mu_peer_e2e; LIST=$TB; sub $TS 'h[245:232]>pe_last[h[231:230]]' 'h[245:230]>peer_last_epoch';;
 # cohort single-active (the original rule): the second user's begin is not ready
 co1) TB=tb_mu_peer_e2e; LIST=$TB; sub $CO '!act[ub] && !idf' 'act == 4'"'"'d0 && !idf';;
 # lifecycle presents a terminal only when the die is globally drained
 lc1) TB=tb_mu_peer_e2e; LIST=$TB; sub $LC 'wire present = tn != 0 && !gap && (all_drained || !alone_a);' 'wire present = tn != 0 && !gap && all_drained;';;
 # codec holds one terminal at a time (the original): a second accepted terminal while one awaits POST faults
 cd1) TB=tb_mu_peer_e2e; LIST=$TB; sub $CD "if(tq_n==3'd4||term_v[terminal_tag[44:43]])fault<=1;" "if(tq_n!=0||term_v[terminal_tag[44:43]])fault<=1;";;
 # codec checks rank requests against the latest grant only (the original), not the user's allocation
 cd2) TB=tb_mu_peer_e2e; LIST=$TB; sub $CD '(!al_v[d[74:73]]||d[88:30]!=al_tag[d[74:73]]||d[90:89]!=al_gen[d[74:73]])' '(!allocated_valid||d[88:30]!=allocated_tag||d[90:89]!=allocated_gen)';;
 # POST collector posts only on the global die drain
 pc1) TB=tb_mu_peer_e2e; LIST=$TB; sub $PC '(drains||!alone)' '(drains)';;
 # endpoint terminal-barrier release of a retired step waits for the global die drain (pre-PEER rule)
 ep3) TB=tb_mu_peer_e2e; LIST=$TB; sub $EP '(drains||(|c_act))' 'drains';;
 # services hand the POST collector the latest grant as the terminal identity (the original wiring)
 sv1) TB=tb_mu_peer_e2e; LIST=$TB; sub $SV '.terminal_tag(acknowledged_tag),.terminal_gen(acknowledged_generation),' ".terminal_tag({grant_tag[58:43],6'd37,grant_tag[36:0]}),.terminal_gen(grant_generation),";;
 *) echo "MU_PEER $CASE: unknown case"; exit 2;;
esac
[ -f "$L/$LIST.f" ] || { echo "MU_PEER $CASE: no list $LIST"; exit 2; }
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$LIST.f"
if [ -n "$SUBS" ]; then
  python3 - "$W" "$SUBS" <<'PY' || { echo "MU_PEER $CASE: substitution did not apply"; exit 2; }
import sys
w, subs = sys.argv[1], sys.argv[2]
for rec in subs.split('\x1e'):
    if not rec: continue
    f, a, b = rec.split('\x1f')
    p = w + '/' + f; s = open(p).read()
    assert s.count(a) == 1, (f, a, s.count(a))
    open(p, 'w').write(s.replace(a, b))
PY
fi
cd "$W"
if [ "$TB" = lint_peer_mu ]; then
  "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module qkd_hr_core_peer \
    $(cat "$L/$LIST.f") > "$OUT/$CASE.log" 2>&1; rc=$?
  if [ $rc = 0 ] && ! grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$OUT/$CASE.log" \
     && grep -q 'qkd_host_tp8_coordinator_mu root__u_coordinator' rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_peer.v \
     && grep -q 'qkd_host_ctrl_token_service_packet_collected_mu #' rtl/qwen_sys/mu_qwen_20261018/host_cluster_mu/qkd_hr_core_peer.v; then
    echo "PASS LINT_PEER_MU qkd_hr_core_peer (root__u_coordinator = qkd_host_tp8_coordinator_mu, u_ctrl = token service _mu, MU 1; $(wc -l < "$L/$LIST.f") sources)" >> "$OUT/$CASE.log"
  else echo "FAIL LINT_PEER_MU rc=$rc" >> "$OUT/$CASE.log"; fi
  echo "MU_PEER $CASE: $(tail -1 "$OUT/$CASE.log")"; grep -q '^PASS' "$OUT/$CASE.log"; exit
fi
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j ${VJ:-4} -o sim $(cat "$L/$LIST.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU_PEER $CASE: BUILD-ERR"; grep -E '%Error' "$OUT/$CASE.build" | head -20; exit 1; }
./obj/sim $PA > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "MU_PEER $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
