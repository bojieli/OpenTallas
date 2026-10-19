# QW-KVATTN: the qualified static attention service (_sr = qkd_attn_service_root, KVJ-B2 build, Verilator 5.050) on the
# REAL TP4-operand vectors of L0 / L1 P8191 (kv_attn_vectors.py), calendar = the KVJ-B2 T8192 compiler calendar
set -u
W=/srv/opentallas-scratch/claude/qw-kvattn-1018; B=/srv/opentallas-scratch/claude/kvj-b2-1017
CAL=029902990299034f052e04e50494019d038f019601a5
mkdir -p $W/svc; cd $W
run() { local bin=$1 name=$2 vec=$3 mode=$4; local O=$W/svc/$name; mkdir -p $O; local T=$(cat $vec/ctx)
  /usr/bin/time -f "%e s %M KB" -o $O/time $B/$bin/parent0/Vtb_qwen_tp8_attention_native_service_w16 +VEC=$vec +CTX=$T +MODE=$mode +CAL=$CAL > $O/native.log 2>&1; echo $? > $O/exit; }
for v in vec/L*; do n=$(basename $v); run b_sr sr_$n $v steady & done; wait
for v in vec_shift/L0_d0_g0 vec_shift/L0_d2_g1 vec_pos/L0_d0_g0 vec_pos/L0_d2_g1; do n=$(echo $v | tr / _); run b_sr sr_mut_$n $v steady & done
run b_w16 w16_L0_d0_g0 vec/L0_d0_g0 steady & run b_w16 w16_L1_d3_g1 vec/L1_d3_g1 steady &
wait
for d in svc/*; do echo "$(basename $d) exit=$(cat $d/exit) $(grep '^{' $d/native.log)"; done > svc_summary.txt
