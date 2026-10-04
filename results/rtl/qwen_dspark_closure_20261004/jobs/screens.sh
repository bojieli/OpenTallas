#!/bin/bash
# Qwen DSpark new-hardware SS screens (tools/risk_clock_loops_screen.py: Yosys 0.68 synth (no ORFS adder map),
# OpenSTA SS RVT, 60 ps setup uncertainty; raw + placed/repaired phases).  Run from $R/src on ot-epyc1tb.
R=/srv/opentallas-scratch/claude/qwen-dspark-closure
cd $R/src
S="python3 tools/risk_clock_loops_screen.py"
O=$R/runs
run() { G=$1; L=$2; shift 2; mkdir -p $O; nohup /srv/opentallas-scratch/admit.sh $G -- $S --work $O/$L --output $O/$L.json --label $L "$@" > $O/$L.log 2>&1 & }
SEQ="--param N=4 --param NW=18 --param PAW=12 --param VWA=12 --param DAW=6 --param FW=512 --param TAGW=32 --param QWEN_FULLSHAPE=1 --param NTOK=8 --param ENABLE_AR256=1"
FSEQ="--focus fsm=^(st|seg)\[ --focus txq=^(q_n|q_w|q_r|rd_k|rd_v|tx_k|rx_k)\[ --focus arp=^(tok_vec|val_vec|n_tok|best_v|best_i|next_token|next_val|nw)\["
for P in 0.833; do T=$(echo $P | tr -d .)
run 8 seqvp_arp1_$T --top ot_qwen_tp_seq_w12_vp --source rtl/rom/ot_qwen_tp_seq_w12_vp.sv $SEQ --param ENABLE_ARP=1 --period-ns $P --domain 1.2GHz-streaming $FSEQ
run 8 seqvp_arp0_$T --top ot_qwen_tp_seq_w12_vp --source rtl/rom/ot_qwen_tp_seq_w12_vp.sv $SEQ --param ENABLE_ARP=0 --period-ns $P --domain 1.2GHz-streaming $FSEQ
run 4 accept_$T --top ot_qwen_combined_dspark_accept --source rtl/qwen_sys/combined/ot_qwen_combined_dspark_accept.sv --source rtl/hdc/ot_hdc_accept.sv --param SNW=18 --param ACCEPT_COMMIT=1 --period-ns $P --domain 1.2GHz-streaming --focus 'acc=(acc_|u_acc)'
done
