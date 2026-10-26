#!/bin/bash
# QW-RSTRLY 10-20: pass + mutant reset-lane benches of the 2 new class kits on the fleet (ot-run, Verilator 5.050)
L=/home/ubuntu/scratch/qw-rstrly/bench_logs; mkdir -p $L
D=/srv/opentallas-scratch/claude/qw-rstrly-1020/src
run() { k=$1; m=$2; shift 2
  /home/ubuntu/bin/ot-run --mem 4 --threads 2 --dir $D -- bash tools/qwen_split/bench_fwd_rst_lane.sh $m /srv/opentallas-scratch/claude/qw-rstrly-1020/runs/${k}_$m "$@" > $L/${k}_$m.log 2> $L/${k}_$m.otrun &
}
E0=qfd_rlyr0_1_EW_65x30; ES=qfd_rlyr_1_EW_65x30; EL=qfd_rlyrl_1_EW_65x30
run qfwd_rlyr_1_en_65x30 pass $E0 qfd_rlyr_1_EN_65x30 $EL; run qfwd_rlyr_1_en_65x30 full $E0 qfd_rlyr_1_EN_65x30 $EL
run qfwd_rlyrl_1_ne_65x30 pass $E0 $ES qfd_rlyrl_1_NE_65x30; run qfwd_rlyrl_1_ne_65x30 land2 $E0 $ES qfd_rlyrl_1_NE_65x30
wait; grep -H "RST_BENCH \(PASS\|FAIL\)\|BUILD_FAILED\|masters" $L/*.log; grep -h "RAN on\|NOT RUN" $L/*.otrun | sort | uniq -c
