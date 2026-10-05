#!/bin/bash
# HA8 vehicle at P8191 (TP2, --winw 224, gold tp2_l3) with the ME arithmetic contract: build, then one SRAM layer (L0)
# and one HBM layer (L2), each from the GPU golden exit of the previous layer.  Usage: vehicle.sh <label> "<build args>"
R=/srv/opentallas-scratch/claude/hbm-fmax-qme; Q=/srv/opentallas-scratch/claude/qwen-hbmacc-8k
lab=$1; bargs=$2; B=$R/runs/build_$lab
cd $R/src
echo "$(date -Is) START build $lab $bargs" >> $R/jobs/MANIFEST
if [ ! -x $B/qwen_hbmacc_rt ]; then
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/qwen_hbmacc_rt_token_w12.py --build-only --workdir $B --tp 2 --winw 224 $bargs --jobs 16 > $R/jobs/build_$lab.log 2>&1 || { echo "$(date -Is) FAIL build $lab" >> $R/jobs/MANIFEST; exit 1; }
fi
for L in ${LAYERS:-L0 L2}; do
  if [ $L = L0 ]; then PR=5000; SRCD=$Q/runs/a_p8191/L0; else PR=655; SRCD=$Q/runs/a_p8191_w224/$L; fi
  W=$R/runs/${lab}_$L; mkdir -p $W; cp $SRCD/stages.txt $SRCD/preload.hex $W/
  ( /srv/opentallas-scratch/admit.sh 4 -- python3 tools/qwen_hbmacc_rt_token_w12.py --workdir $W --build-dir $B --tp 2 --winw 224 $bargs \
     --stages $W/stages.txt --layout /home/ubuntu/w12/img6144/L0-d0/layer0_rom.json --oracle-dir $Q/gold/tp2_l3/P8191 \
     --preload $W/preload.hex --pos 8191 --token 24 --preroll $PR --threads 4 --kv-dir $Q/gold/tp2_l3/P8191/kv_pre > $W/driver.log 2>&1
    echo "$(date -Is) END run ${lab}_$L rc=$?" >> $R/jobs/MANIFEST ) &
done
wait
