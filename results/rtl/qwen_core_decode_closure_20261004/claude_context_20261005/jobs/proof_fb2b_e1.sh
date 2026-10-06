#!/bin/bash
# exactness of DEC_LA core --dec-la-issue-fb 2 --dec-la-bound 1 on the five adopted 8K benches (same plans/goldens as proof/h); each run exits nonzero on any mismatch
R=/srv/opentallas-scratch/claude/qwen-core-decode; B=/srv/opentallas/scratch-overflow/claude/qwen-core-ctx/e1
cd /srv/opentallas/scratch-overflow/claude/qwen-core-ctx/psrc_440c091b2
echo "$(date -Is) build fb2b_e1 src=440c091b224a50ade751002af107ebf2079bc0f4 opts=--dec-la-issue-fb 2 --dec-la-bound 1" >> $B/STATUS_fb2b_e1.md
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/qwen_rom_rt_vprm_w12.py --workdir $B/bld_fb2b_e1/w --build-dir $B/bld_fb2b_e1 --hbm-layers 3 --code-banks 1 --build-only --dec-la-issue-fb 2 --dec-la-bound 1 > $B/build_fb2b_e1.log 2>&1
echo $? > $B/build_fb2b_e1.rc
echo "$(date -Is) build rc=$(cat $B/build_fb2b_e1.rc)" >> $B/STATUS_fb2b_e1.md
[ "$(cat $B/build_fb2b_e1.rc)" = 0 ] || exit 1
bash results/rtl/qwen_core_decode_closure_20261004/jobs/proof_pve1.sh /srv/opentallas/scratch-overflow/claude/qwen-core-ctx/psrc_440c091b2 $B/bld_fb2b_e1 fb2b_e1 --dec-la-issue-fb 2 --dec-la-bound 1
echo "$(date -Is) proof done: $(cat $R/proof/fb2b_e1/runs/*.rc | tr '\n' ' ')" >> $B/STATUS_fb2b_e1.md
