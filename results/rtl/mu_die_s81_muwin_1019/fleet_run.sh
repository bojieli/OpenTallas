#!/bin/bash
# MU-DIE-S81/MUWIN fleet chain (v2 = LINECOL-merged compiler): compiled MU window tables on dsdv_seq_host_mux (5dd45e769 RTL)
cd $(dirname $0); G=repo/rtl/dsrom_sys/s81_dv/unit/test/run_mu_win_prog_bench.sh
bash $G prog_L0_mu_A mu2 out_L0_u012 0,1,2 > gate_L0_u012.log 2>&1; echo "L0 u012 rc $?"
bash $G prog_L0_mu_A mu2 out_L0_all 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45 > gate_L0_all.log 2>&1; echo "L0 all rc $?"
bash $G prog_L14_mu_A mu2 out_L14A_all 0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44 > gate_L14A_all.log 2>&1; echo "L14A all rc $?"
bash $G prog_L20_mu_A mu2 out_L20A_all 0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44 > gate_L20A_all.log 2>&1; echo "L20A all rc $?"
