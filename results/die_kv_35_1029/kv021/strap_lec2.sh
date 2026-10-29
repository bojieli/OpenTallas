#!/bin/bash
# DIE-KV-35 KV-021: strap LEC (main strap_lec.py) of the re-tied types on the eventA2 sidecar (event27f plan); hub_Wo separate (gen_rtl GenError on rtl-root codex-kv-0822)
cd /srv/opentallas-scratch2/claude/die-kv-35-1029
python3 /srv/opentallas-scratch2/claude/wt/die-kv-33-leaf/tools/die_plan/strap_lec.py /srv/opentallas-scratch2/claude/wt/codex-kv-0822/results/die_kv_29_1029/event27f/plan.json --landing eventA2/sidecar.json --rtl-root /srv/opentallas-scratch2/claude/wt/codex-kv-0822 --out eventA2/strap_lec --types kv3_hg_v1,kv3_hg_v1p3,kv3_hg_v1p6,kv3_hroot,kv3_pc_v1__cl23f6a148,kv3_pc_v1__cl4ea58a5c,kv3_pc_v1__cl7f648944,kv3_pc_v3 --mutant --jobs 4 > eventA2/strap_lec.log 2>&1
echo STRAP_LEC2_RC $? $(date)
