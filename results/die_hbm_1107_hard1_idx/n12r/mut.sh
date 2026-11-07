#!/bin/bash
# mutants of the new core: each must give diff>0
cd /srv/opentallas-scratch3/claude/hbm-hard-1-idx/n12r
N=ot_hbm_idx_vm_query_n12r_core.sv
mkdir -p mut
m(){ sed "$2" $N > mut/$1.sv; cmp -s $N mut/$1.sv && { echo "$1 NOCHANGE"; return; }
 iverilog -g2012 -DRTX=${3:-4} -DSEED=7 -DCYC=${4:-20000} -o mut/$1.vvp gold/*.sv mut/$1.sv tb_n12r.sv 2>&1 | head -3
 echo "$1 $(timeout 500 vvp mut/$1.vvp | grep RESULT)"; }
m m1_prio_lowest 's/for(integer b=0;b<8;b=b+1)if(expected\[b\]&&vm_rr/for(integer b=7;b>=0;b=b-1)if(expected[b]\&\&vm_rr/' &
m m2_qi_delay_short 's/wire\[6:0\]qi_e=qi_dl\[D-1\]/wire[6:0]qi_e=qi_dl[D-2]/' &
m m3_code_delay_short 's/wire\[23:0\]code_e=code\[D-1\]/wire[23:0]code_e=code[D-2]/' &
m m4_sel_order 's/8.d1<<b;\s*$/8'"'"'d128>>b;/' &
m m5_en_only_part 's/ wire en_d=|parts_d;/ wire en_d=\&parts_d;/' &
m m6_wsel_swap 's/wsel_d\[w\*8+:8\]/wsel_d[(1-w)*8+:8]/' &
m m7_qs_code 's/code_d\[l\*3+:3\]={1.b1,2.(s)}/code_d[l*3+:3]={1'"'"'b1,2'"'"'(3-s)}/' &
m m8_ws_bit 's/{1.b0,1.b1,1.(s)}/{1'"'"'b0,1'"'"'b1,1'"'"'(1-s)}/' &
m m9_rep_stuck_g5 's/if(c\[8\])block_data\[p\*256+g\*32+:32\]<=m0|m1/if(c[8]\&\&g!=5)block_data[p*256+g*32+:32]<=m0|m1/' &
m m10_seen_stuck 's/if(wv\[1\])weight_seen\[1\]<=1;/if(wv[0])weight_seen[1]<=1;/' &
m m11_bad_drop 's/if(parts!=4.hf||weight_seen!=2.b11)bad<=1;/if(weight_seen!=2'"'"'b11)bad<=1;/' &
m m12_qid_wrong 's/block_number<=qid\[1:0\]/block_number<=qid[2:1]/' &
wait
echo MUT_DONE
