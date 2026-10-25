#!/bin/bash
cd /srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
B=/srv/opentallas-scratch/claude/rtlc_bench/stn; mkdir -p $B
run(){ n=$1; shift; ( "$@" > $B/$n.txt 2>&1; echo "rc=$?" >> $B/$n.txt ) & }
D=tools/s81/rtl_delay_eq.py
run qN python3 $D --top dsfd_qbank_N --file rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv --out $B/qN --default async
run qN_mut python3 $D --top dsfd_qbank_N --file rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv --out $B/qN_mut --default async --dut-rev origin/main
run qS python3 $D --top dsfd_qbank_S --file rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv --out $B/qS --default rel1
run qS_mut python3 $D --top dsfd_qbank_S --file rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv --out $B/qS_mut --default rel1 --dut-rev origin/main
run rg python3 $D --top dsfd_rstg --file rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv --out $B/rg --cls "i[0]=async"
run rg_mut python3 $D --top dsfd_rstg --file rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv --out $B/rg_mut --cls "i[0]=async" --dut-rev origin/main
run sp bash tools/s81_static_net/bench_sstn_split.sh pass $B/sp
for m in base_data_1flop payload_1flop base_control base_status_unreg payload_bit payload_reset payload_edge; do run sp_$m bash tools/s81_static_net/bench_sstn_split.sh $m $B/sp_$m; done
wait
