#!/bin/bash
# One stage at P8191 in the HA8 vehicle with successors: veh.sh <a|b> <stage> <label> <snapshot> <successor flags...>
# Inputs (stages, preload, oracle, KV, design point) are the qwen-hbmacc-8k fork's w224 jobs (runs/{a,b}_p8191_w224/<stage>).
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore; K=/srv/opentallas-scratch/claude/qwen-hbmacc-8k
b=$1; st=$2; lab=$3; src=$4; shift 4
J=$K/runs/${JRUN:-${b}_p8191_w224}/$st; W=$R/veh/$lab/$st; mkdir -p $W; rm -f $W/exit; cp $J/{stages.txt,preload.hex} $W/
# the fork's command line, with our tool, workdir, build dir and the successor flags
args=$(sed -e 's#^.*qwen_hbmacc_rt_token_w12.py ##' $J/cmd.txt)
args=$(echo "$args" | sed -e "s#--workdir [^ ]*#--workdir $W#" -e "s#--build-dir [^ ]*#--build-dir $R/veh/build_${lab}_$b#" \
  -e "s#--stages [^ ]*#--stages $W/stages.txt#" -e "s#--preload [^ ]*#--preload $W/preload.hex#")
/srv/opentallas-scratch/admit.sh 20 -- /usr/bin/python3 $R/$src/tools/qwen_hbmacc_rt_token_w12_f12.py "$@" $args > $W/driver.log 2>&1
echo "rc=$?" > $W/exit
