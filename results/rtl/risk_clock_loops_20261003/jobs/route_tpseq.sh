#!/bin/bash
# Routed SS/FF authority for the Qwen TP sequencer at 1.2 GHz (0.833 ns) and at the 0.9 GHz serial domain (1.111 ns).
cd ~/rcl-20261003/src
export OT_ORFS_NUM_CORES=16
for P in 0.833 1.111; do
  T=$(echo $P | tr -d .)
  W=../routes/qwen_tp_seq_$T; mkdir -p $W
  ( python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_tp_seq_w12 --source rtl/rom/ot_qwen_tp_seq_w12.sv \
      --param ENABLE_AR256=0 --param N=4 --param NW=18 --param QWEN_FULLSHAPE=1 \
      --clock-period-ns $P --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
      --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
      --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
      --slew-margin-percent 30 --purpose signoff_target --nickname-tag rcl_tpseq_$T \
      --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
    echo "rc=$?" > $W/exit
    python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
    echo "corner_rc=$?" >> $W/exit ) &
done
wait
