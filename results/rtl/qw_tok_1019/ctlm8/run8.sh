#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch/claude/qw-ctlm8r4-1020
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; bash chain7.sh' > $R/chain8.log 2>&1; echo "CHAIN_RC $?" >> $R/chain8.log
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'bash depth7.sh' > $R/depth8.log 2>&1; echo "DEPTH_RC $?" >> $R/depth8.log
cd $R/oldsrc && bash bench8.sh > $R/bench8.log 2>&1; echo "BENCH_RC $?" >> $R/bench8.log
echo RUN8_DONE
