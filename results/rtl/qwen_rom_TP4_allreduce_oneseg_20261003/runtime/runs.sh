#!/bin/bash
# A/B/C on one AR256-enabled build (ENABLE_AR256=1 decodes only count-0 AR descriptors; pinned 128-word images run unchanged)
cd /home/ubuntu/qar1/src
B="--tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --threads 7 --jobs 8 --coll-lat 339 --enable-ar256"
O="--token-oracle /home/ubuntu/w12/oracle_tp4 --preload /tmp/qwen-vocab-embed-token0/vm_x_fp32.hex"
for r in runA runB runC; do
  rm -rf /home/ubuntu/qar1/$r && cp -al /home/ubuntu/qar1/bld /home/ubuntu/qar1/$r && rm -f /home/ubuntu/qar1/$r/qwen_rom_rt /home/ubuntu/qar1/$r/*.log /home/ubuntu/qar1/$r/*.rss
done
python3 tools/qwen_rom_rt_token_w12.py --workdir /home/ubuntu/qar1/runA --stages /home/ubuntu/qar1/stages_base_L0L1.txt $O $B --coll-depth 1024 --result /home/ubuntu/qar1/res/runA_split128_d1024.json > /home/ubuntu/qar1/runA.out 2>&1 &
python3 tools/qwen_rom_rt_token_w12.py --workdir /home/ubuntu/qar1/runB --stages /home/ubuntu/qar1/img256/stages.txt $O $B --coll-depth 1024 --result /home/ubuntu/qar1/res/runB_one256_d1024.json > /home/ubuntu/qar1/runB.out 2>&1 &
python3 tools/qwen_rom_rt_token_w12.py --workdir /home/ubuntu/qar1/runC --stages /home/ubuntu/qar1/img256/stages.txt $O $B --coll-depth 256 --result /home/ubuntu/qar1/res/runC_one256_d256.json > /home/ubuntu/qar1/runC.out 2>&1 &
wait
echo ALLDONE
