#!/bin/bash
# W10b: re-pin the product bank map at 4b4b12e2 (41 stages, VM counted once) (main's tools/uarch_model.py; same 37-stage owners)
cd /home/ubuntu/w10s
OUT=/tmp/claude-1000/w10out/prod_4b4b; mkdir -p $OUT; git rev-parse HEAD > $OUT/SOURCE_SHA
nice -n 5 python3 tools/v41_rom_ksplit_bankmap.py --snapshot /home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277 \
  --output $OUT/v41_rom_ksplit_bankmap_product.json --draws 50 --near --wire --owners results/arch/v41_stage_owner_product.json > $OUT/prod.log 2>&1
echo EXIT $? >> $OUT/prod.log
