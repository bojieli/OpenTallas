#!/bin/bash
# One TP2 layer (L2) at P8191 in the HA8 vehicle with successors: veh_l2.sh <label> <snapshot> <successor flags...>
# Inputs (stages, preload, oracle, KV) are the qwen-hbmacc-8k fork's w224 L2 job; baseline 33,058 cycles exact.
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore; K=/srv/opentallas-scratch/claude/qwen-hbmacc-8k
lab=$1; src=$2; shift 2
W=$R/veh/$lab; mkdir -p $W; cp $K/runs/a_p8191_w224/L2/{stages.txt,preload.hex} $W/
/srv/opentallas-scratch/admit.sh 20 -- /usr/bin/python3 $R/$src/tools/qwen_hbmacc_rt_token_w12_f12.py "$@" --workdir $W --build-dir $R/veh/build_$lab \
  --stages $W/stages.txt --layout /home/ubuntu/w12/img6144/L0-d0/layer0_rom.json --oracle-dir $K/gold/tp2_l3/P8191 \
  --preload $W/preload.hex --pos 8191 --token 24 --preroll 655 --threads 4 --winw 224 --kv-dir $K/gold/tp2_l3/P8191/kv_pre > $W/driver.log 2>&1
echo "rc=$?" > $W/exit
