#!/bin/bash
# safe-qwen A6 gate: Qwen ROM L0 (golden entry, stream4 real-mem, as fullbw-hbm/runs/rt/L0_iso) with FQ_HEAD=1 and the FQ_HEAD=0 control
cd /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/src
for v in 1 0; do
  W=/srv/opentallas/scratch-overflow/claude/safe-qwen-tok/fqh$v
  if [ $v = 1 ]; then DRV="python3 /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/src/tools/safe_qwen/fqh_token.py /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/src/tools/qwen_rom_rt_token_stream4_w12.py"; else DRV="python3 /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/src/tools/qwen_rom_rt_token_stream4_w12.py"; fi
  ( RT_PROGRESS=1 /srv/opentallas-scratch/admit.sh 24 -- /usr/bin/time -f "%M %e %U %S" -o $W/time.txt $DRV --real-mem --stream4      --workdir $W/w --build-dir $W/build --stages /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/stages.txt --oracle /srv/opentallas-scratch/claude/realmem-ctx8k/gold/P8191      --pos 8191 --token 24 --enable-ar256 --coll-depth 256 --hbm-layers 3 --wbw 4 --threads 4 --x-preload /srv/opentallas/scratch-overflow/claude/safe-qwen-tok/entry.hex      --result $W/result.json > $W/driver.log 2>&1; echo $? > $W/exit ) &
done
wait
