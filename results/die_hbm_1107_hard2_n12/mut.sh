#!/bin/bash
cd /srv/opentallas-scratch3/claude/hbm-hard-2-n12/n12s
N=ot_hbm_idx_vm_query_n12s_core.sv
G=/srv/opentallas-scratch3/claude/hbm-hard-1-idx/n12r/gold
mkdir -p mut
m(){ sed "$2" $N > mut/$1.sv; cmp -s $N mut/$1.sv && { echo "$1 NOCHANGE"; return; }
 iverilog -g2012 -DRTX=4 -DSEED=7 -DCYC=30000 -o mut/$1.vvp $G/*.sv mut/$1.sv tb3.sv 2>&1 | head -3
 echo "$1 $(timeout 500 vvp mut/$1.vvp | grep RESULT | cut -c1-170)"; }
m s1_qi_short 's/wire\[6:0\]qi_e=tqi\[D-1\]/wire[6:0]qi_e=tqi[D-2]/' &
m s2_hi_short 's/wire thi_e=thi\[D-1\]/wire thi_e=thi[D-2]/' &
m s3_tq_short 's/wire tq_e=tq\[D-1\]/wire tq_e=tq[D-2]/' &
m s4_tw_short 's/wire tw_e=tw\[D-1\]/wire tw_e=tw[D-2]/' &
m s5_hi_pol 's/wire qhi=qsum\[0\]/wire qhi=!qsum[0]/' &
m s6_sum_noqi 's/+14.(query_index);/;/' &
m s7_sid_nobit15 's/wire q_sid_ok=qsum\[13\]||/wire q_sid_ok=/' &
m s8_wsid_nobit15 's/wire w_sid_ok=weight_sector\[15\]||/wire w_sid_ok=/' &
m s9_sum_narrow 's/qsum\[12:11\]==sid/qsum[12:11]==sid||qsum[10]/' &
wait
m s10_nofault_sid 's/if(sid_bad||rrv!=expected)/if(rrv!=expected)/' &
m s11_nofault_rr 's/if(sid_bad||rrv!=expected)/if(sid_bad)/' &
m s12_rq_nogate 's/rq_v<=sid_bad?8.d0:(q_req|w_req)/rq_v<=q_req|w_req/' &
m s13_rq_s 's/{qsum,2.(b)}/{qsum,2'"'"'(3-b)}/' &
m s14_rq_w 's/2.d0,1.(b)}/2'"'"'d0,1'"'"'(1-b)}/' &
m s15_rep_stuck 's/if(c\[2\])block_data/if(c[2]\&\&g!=5)block_data/' &
m s16_en_and 's/ wire en_d=|parts_d;/ wire en_d=\&parts_d;/' &
m s17_wv_swap 's/if(c)weights\[w\*256+g\*32+:32\]<=res_d\[w\*256/if(c)weights[w*256+g*32+:32]<=res_d[(1-w)*256/' &
m s18_hi_lo 's/&res_d\[(p+4)\*256+g\*32+:32\]/\&res_d[p*256+g*32+:32]/' &
wait
m s19_qid 's/block_number<=qid\[1:0\]/block_number<=qid[2:1]/' &
m s20_seen 's/if(wv\[1\])weight_seen\[1\]<=1;/if(wv[0])weight_seen[1]<=1;/' &
m s21_parts 's/if(parts!=4.hf||weight_seen!=2.b11)bad<=1;/if(weight_seen!=2'"'"'b11)bad<=1;/' &
m s22_w_tag 's/tw\[0\]<=weight_slot&&w_sid_ok/tw[0]<=weight_slot/' &
m s23_q_tag 's/tq\[0\]<=query_slot&&q_sid_ok/tq[0]<=query_slot/' &
m s24_expected 's/{2{(tq_e&&!thi_e)||tw_e}}/{2{(tq_e\&\&!thi_e)}}/' &
wait
echo MUT_DONE
