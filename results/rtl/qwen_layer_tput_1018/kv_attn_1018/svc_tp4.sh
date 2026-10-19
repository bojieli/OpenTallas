# QW-KVATTN: the same service runs with gold = the TP4 ISA attention output (isa.hex): expected FAIL (P.V split 256 vs 512)
set -u
W=/srv/opentallas-scratch/claude/qw-kvattn-1018; B=/srv/opentallas-scratch/claude/kvj-b2-1017
CAL=029902990299034f052e04e50494019d038f019601a5
cd $W
for n in L0_d0_g0 L1_d0_g0; do V=$W/vec_tp4gold/$n; mkdir -p $V; cp vec/$n/q.hex vec/$n/kv.hex vec/$n/ctx $V/; cp vec/$n/isa.hex $V/gold.hex
 O=$W/svc/sr_tp4gold_$n; mkdir -p $O
 ( $B/b_sr/parent0/Vtb_qwen_tp8_attention_native_service_w16 +VEC=$V +CTX=8192 +MODE=steady +CAL=$CAL > $O/native.log 2>&1; echo $? > $O/exit ) &
done; wait
for d in svc/sr_tp4gold_*; do echo "$(basename $d) exit=$(cat $d/exit) $(grep '^{' $d/native.log)"; done > svc_tp4_summary.txt
