#!/bin/bash
cd /home/ubuntu/qar1/src
A="--tp 4 --coll-lat 339 --coll-depth 1024 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --threads 14 --jobs 24 --enable-ar256"
python3 tools/qwen_rom_rt_token_w12.py --workdir /home/ubuntu/qar1/bld --stages /dev/null --token-oracle /home/ubuntu/w12/oracle_tp4 --preload /tmp/qwen-vocab-embed-token0/vm_x_fp32.hex $A --build-only
echo rc=$?
