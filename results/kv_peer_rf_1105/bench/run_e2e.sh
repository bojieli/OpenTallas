#!/bin/bash
# DIE-KV-70 11-04 peer form bench: rtl/test/mu_qwen_1018/tb_mu_peer_e2e on the r3 form (coordinator chain + rank codecs).
# usage: run_e2e.sh OUT CASE   (repo root as cwd).  CASE: base | form | form_uid | form_abort | form_abort_uid | MUT name (see below; must FAIL)
set -u
OUT=$(mkdir -p "$1" && cd "$1" && pwd); CASE=$2; ROOT=$(pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
R3=results/kv_peer_rf_1105/rtl/qkd_hr_core_peer
TBF=rtl/test/mu_qwen_1018/tb_mu_peer_e2e.sv
W=$OUT/src_$CASE; rm -rf $W; mkdir -p $W
while read -r f; do mkdir -p $W/$(dirname $f); cp $f $W/$f; done < rtl/test/mu_qwen_1018/lists/tb_mu_peer_e2e.f
LIST=$(cat rtl/test/mu_qwen_1018/lists/tb_mu_peer_e2e.f)
PA=""
sub(){ python3 -I - "$W/$1" "$2" "$3" <<'PY' || { echo "SUBST FAIL $1: $2"; exit 2; }
import sys
p,a,b=sys.argv[1:4]; s=open(p).read(); assert s.count(a)>=1,(p,a); open(p,'w').write(s.replace(a,b))
PY
}
FORM=1
case $CASE in
 base) FORM=0;;
 base_abort) FORM=0; PA=+ABORT;;
 form) ;;
 form_uid) sub $TBF 'parameter integer UIDSLOT=0;' 'parameter integer UIDSLOT=1;';;
 form_abort) PA=+ABORT;;
 form_abort_uid) PA=+ABORT; sub $TBF 'parameter integer UIDSLOT=0;' 'parameter integer UIDSLOT=1;';;
esac
if [ $FORM = 1 ]; then
 mkdir -p $W/$R3; cp $R3/*.sv $W/$R3/; LIST="$LIST $(cd $W; ls $R3/*.sv)"
 sub $TBF 'qkd_host_tp8_coordinator_mu #(.MU(1),.POST_UID_SLOT(UIDSLOT)) co(' 'qkd_host_tp8_coordinator_r3 #(.MU(1),.POST_UID_SLOT(UIDSLOT)) co('
 sub $TBF 'qkd_host_peer_rank_codec #(.RANK(d))rc(' 'qkd_host_peer_rank_codec_r3 #(.RANK(d))rc('
 # form round 2 (frame choice register, request stage): measured overlap_dispatch 6 of 12, source 10; limit moved from 8 to 6, perf loss accepted
 sub $TBF 'if(overlap_disp<4*ROUNDS-4)fail' 'if(overlap_disp<4*ROUNDS-6)fail'
 sed -i -e 's/co\.g_mu\.u_lifecycle\.g_mu\.u_lifecycle\.g_mu\./co.u_lifecycle.u_lifecycle./g' -e 's/co\.g_mu\.u_peer\.g_mu\./co.u_peer./g' -e 's/co\.g_mu\./co./g' $W/$TBF
fi
LC=$R3/qkd_host_lifecycle_r3.sv; CD=$R3/qkd_host_peer_coordinator_codec_r3.sv; CO=$R3/ot_qwen_tp8_token_cohort_r3.sv; AL=$R3/ot_qwen_tp8_token_epoch_allocator_r3.sv; RK=$R3/qkd_host_peer_rank_codec_r3.sv; PC=$R3/qkd_host_post_collector_r3.sv; TP=$R3/qkd_host_tp8_coordinator_r3.sv
case $CASE in
 # a terminal is presented without its registered identity stage: stale identity_ok_q must fault or hang
 m_hdvv) sub $LC 'wire present_d = hd_vv &&' 'wire present_d = hd_v &&';;
 # acknowledged identity reads the wrong user head
 m_ack) sub $LC 'assign acknowledged_tag = hd_tag;' 'assign acknowledged_tag = t_tag[hd_u+2'"'"'d1];';;
 # cancel acceptance by identity without the retired-identity flag (abort case)
 m_clt) PA=+ABORT; sub $LC '&& (c_pp || c_lt) && same_q[r];' '&& (c_pp) && same_q[r];';;
 # request ack frame carries the wrong rank's tag
 m_rat) sub $CD 'i_data[k*512+30+:59]=participant_tag[k*59+:59];' 'i_data[k*512+30+:59]=participant_tag[((k+1)%8)*59+:59];';;
 # terminal class5 frames read the head before it is loaded
 m_acc) sub $CD 'if(start_q)begin accepted_tag<=tq_tag[tq_r];accepted_gen<=tq_gen[tq_r];end' 'if(tq_start)begin accepted_tag<=tq_tag[tq_r];accepted_gen<=tq_gen[tq_r];end';;
 # allocation dirty cleared without a frame: rank never sees the change
 m_dirty) sub $CD 'if(allocation_change)allocation_dirty[i]<=1;' 'if(allocation_change)allocation_dirty[i]<=0;';;
 # cohort face does not wait for the registered payload
 m_usq) sub $CO 'assign cohort_tag = ctag_r;' 'assign cohort_tag = ctag_r^59'"'"'d1;';;
 # cohort participant join drops the registered pulse
 m_join) sub $CO 'if (req_v_q[r]) begin' 'if (req_v_q[r]&&r!=3) begin';;
 # rank status dirty never set
 m_stat) sub $RK 'if(status!=status_prev)status_dirty<=1;' 'if(status!=status_prev)status_dirty<=0;';;
 # engine result stage loses the tag
 m_rs) sub $TP 'rs_tag<=engine_result_tag;' 'rs_tag<=engine_result_tag^59'"'"'d64;';;
 # POST collector retire without the token
 m_ret) sub $PC 'retired[ur]<=1;cq_needed[ur]<=step_retire_cq;' 'cq_needed[ur]<=step_retire_cq;';;
 # grant handshake not held while a terminal waits: (expected to remain PASS unless bench reaches it, reported)
 m_hold) sub $AL 'grant_pending && !grant_hold &&' 'grant_pending &&';;
 # round 2 / 3 cuts
 # cancel capture ignores a pending POST of that user (abort case)
 m_wgo) PA=+ABORT; sub $LC 'wire w_go = w_v && (|(w_oh & cancel_valid)) && !sel4(tp, w_u) && !sel4(pp, w_u) &&' 'wire w_go = w_v && (|(w_oh & cancel_valid)) && !sel4(tp, w_u) &&';;
 # cancel candidates never reach capture (abort case): cancels must hang or fail
 m_cand) PA=+ABORT; sub $LC 'w_v <= |cand_q;' 'w_v <= 0;';;
 # frame choice is not cleared after a transfer: duplicate frames
 m_choice) sub $CD 'tx_seq[i]<=tx_seq[i]+1'"'"'b1;choice[i*4+:4]<=0;' 'tx_seq[i]<=tx_seq[i]+1'"'"'b1;';;
 # token request stage corrupts the token
 m_req) sub $TP 'rq_tok<=token_request_token;' 'rq_tok<=token_request_token^18'"'"'d1;';;
 # registered request check ignores the user's busy flag
 m_reqok) sub $AL 'req_ok_q <= request_valid && !request_ready && !sel4(ubusy, ureq) &&' 'req_ok_q <= request_valid && !request_ready &&';;
 # presentation does not fall with the acceptance: a terminal can present twice
 m_pres) sub $LC 'wire present_d = hd_vv && !alloc_terminal_accepted &&' 'wire present_d = hd_v &&';;
 # POST head register ignored the queue: always user 0
 m_h) sub $PC 'h<=pq[pr];' 'h<=2'"'"'d0;';;
 # terminal queue pop ignores the retire
 m_pop) sub $CD 'wire tq_pop=post_retired;' 'wire tq_pop=1'"'"'b0;';;
 base*|form*) ;;
 *) echo "unknown $CASE"; exit 2;;
esac
cd $W
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module tb_mu_peer_e2e -Mdir obj -j ${VJ:-4} -o sim $LIST > $OUT/$CASE.build 2>&1 || { echo "E2E $CASE BUILD-ERR"; grep -E '%Error' $OUT/$CASE.build | head -20; exit 1; }
timeout 300 ./obj/sim $PA > $OUT/$CASE.log 2>&1; rc=$?
echo "E2E $CASE rc=$rc: $(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' $OUT/$CASE.log | tail -1 | cut -c1-200)"
rm -rf obj
