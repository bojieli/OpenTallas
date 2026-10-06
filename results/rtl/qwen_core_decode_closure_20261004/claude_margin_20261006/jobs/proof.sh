#!/bin/bash
# exactness of the margin core (FB3 + BOUND + AMQ + NXREG) on the five adopted 8K benches (same plans/goldens as proof/h)
set -u
SRC=$1; TAG=$2
B=/srv/opentallas/scratch-overflow/claude/qwen-core-ctx/margin; mkdir -p $B
OPTS="--dec-la-issue-fb 3 --dec-la-bound 1 --dec-la-amq 1 --dec-la-nxreg 1 ${MEIF_OPT:-}"
cd $SRC
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/qwen_rom_rt_vprm_w12.py --workdir $B/bld_$TAG/w --build-dir $B/bld_$TAG --hbm-layers 3 --code-banks 1 --build-only $OPTS > $B/build_$TAG.log 2>&1
echo $? > $B/build_$TAG.rc
[ "$(cat $B/build_$TAG.rc)" = 0 ] || exit 1
bash results/rtl/qwen_core_decode_closure_20261004/jobs/proof_pve1.sh $SRC $B/bld_$TAG $TAG $OPTS
