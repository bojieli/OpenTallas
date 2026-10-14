#!/bin/bash
# die_chain_launch.sh <commit> <tag> [host] [recipe .opts, default v5] -- s81-die-iter: snapshot <commit> (git archive) to
# /srv/opentallas-scratch/claude/s81-die-iter/src_<sha4> on <host> and start tools/s81/die_iter_chain.sh with the v5 recipe
# in .../<tag> (GEN -> IR || clock plan -> kit -> PLACE -> full-die GRT -> STA TT/FF/SS -> die_sens.sh).
# Staged for contract v12 (c4); start it only after the running reference chain has reported (one full-die GRT at a time).
set -euo pipefail
C=$1; TAG=$2; H=${3:-ot-epyc1tb}; R=${4:-results/physical/die_iter_1012/s81/s81_layer1_v5.opts}
D=/srv/opentallas-scratch/claude/s81-die-iter
SHA=$(git -C "$(dirname "$0")/../.." rev-parse "$C"); S=$D/src_${SHA:0:4}
ssh -o ControlPath=none "$H" "test -s $S/SOURCE_SHA" || git -C "$(dirname "$0")/../.." archive "$SHA" | ssh -o ControlPath=none "$H" "mkdir -p $S && tar x -C $S && echo $SHA > $S/SOURCE_SHA"
ssh -o ControlPath=none "$H" "test ! -e $D/$TAG && cd $S && setsid nohup bash tools/s81/die_iter_chain.sh $S $R $D/$TAG $TAG 24 > $D/$TAG.out 2>&1 < /dev/null & echo launched $TAG on $H from $SHA"
