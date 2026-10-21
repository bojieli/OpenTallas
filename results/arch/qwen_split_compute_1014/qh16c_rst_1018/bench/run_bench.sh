#!/bin/bash
# Q-H16C-RST: run pass + mutant reset-lane benches per class kit on the fleet (ot-run, Verilator 5.050)
L=/home/ubuntu/scratch/qh16c-rst/bench_logs; mkdir -p $L
D=/srv/opentallas-scratch/claude/qh16c-rst/src
run() { # kit mode masters...
  k=$1; m=$2; shift 2
  /home/ubuntu/bin/ot-run --mem 4 --threads 2 --dir $D -- bash tools/qwen_split/bench_fwd_rst_lane.sh $m /srv/opentallas-scratch/claude/qh16c-rst/runs/${k}_$m "$@" > $L/${k}_$m.log 2> $L/${k}_$m.otrun &
}
E0=qfd_rlyr0_1_EW_65x30; ES=qfd_rlyr_1_EW_65x30; EL=qfd_rlyrl_1_EW_65x30
run qfwd_rlyr0_1_ns_65x30 pass qfd_rlyr0_1_NS_65x30 $ES $EL; run qfwd_rlyr0_1_ns_65x30 full qfd_rlyr0_1_NS_65x30 $ES $EL
for s in qfd_rlyr_1_EW_65x30 qfd_rlyr_1_NE_65x30 qfd_rlyr_1_NS_65x30; do k=qfwd_$(echo ${s#qfd_} | tr A-Z a-z); run $k pass $E0 $s $EL; run $k full $E0 $s $EL; done
for l in qfd_rlyrl_1_EN_65x30 qfd_rlyrl_1_EW_65x30; do k=qfwd_$(echo ${l#qfd_} | tr A-Z a-z); run $k pass $E0 $ES $l; run $k land2 $E0 $ES $l; done
wait; grep -H "RST_BENCH \(PASS\|FAIL\)\|BUILD_FAILED" $L/*.log; grep -h "RAN on" $L/*.otrun | sort | uniq -c
