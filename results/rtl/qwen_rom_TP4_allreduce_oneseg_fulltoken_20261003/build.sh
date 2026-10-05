#!/bin/bash
cd /home/ubuntu/lpsim-20261003
python3 tool/qwen_rom_layer_parallel_sim.final.py --build --workdir build-ar256-7d736e8e6 --source-root src-7d736e8e6 -- --tp 4 --groups 6144 --count-width 18 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --scale-local 0 --code-banks 5 --coll-lat 339 --coll-depth 256 --enable-ar256 --jobs 16 > build-ar256.out 2>&1
echo rc=$? > build-ar256.rc
