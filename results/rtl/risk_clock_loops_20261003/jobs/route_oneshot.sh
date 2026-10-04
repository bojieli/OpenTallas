#!/bin/bash
# Routed SS/FF authority for the Qwen per-die one-shot collective engine (credit / pop loop) at 1.2 GHz.
cd ~/rcl-20261003/src
export OT_ORFS_NUM_CORES=16
P=0.833; W=../routes/qwen_oneshot_die_d32_0833; mkdir -p $W
~/bin/admit.sh 40 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_rom_oneshot_die \
  --source rtl/rom/ot_rom_oneshot_allreduce.sv --source rtl/proto/ot_fp32_add_rne_pipe.sv \
  --param N=4 --param RANK=0 --param LANES=16 --param TAGW=32 --param DEPTH=32 \
  --clock-period-ns $P --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag rcl_oneshot_d32 \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
