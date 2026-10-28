#!/usr/bin/env bash
# HBM-CORES-REBAL-9 (intel2): wait for the epyc2 token build (ot-run pid $1) then run the 8 phases in parallel on epyc2.
R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-9
while kill -0 $1 2>/dev/null; do sleep 120; done
grep -q SU_MULTIRATE_BUILD_COMPLETE $R/tok_build.otrun.log || { echo "$(date) BUILD NOT COMPLETE, no phases" >> $R/tok_chain.log; exit 1; }
echo "$(date) build complete, launching phases" >> $R/tok_chain.log
~/.local/bin/ot-run --mem 240 --threads 8 --hosts epyc2 --dir /srv/opentallas-scratch2/claude/wt/hbm-cores-rebal-9 -- bash -c \
 "cd $R && /usr/bin/time -v -o $R/tok_m5w1/gate.time bash -c 'for p in POS DATA ADDR RF RED CAL EPOCH BRIDGE_LEAF; do bash $R/tok_phase.sh $R/tok_m5w1 \$p & done; wait'; cat $R/tok_m5w1/phase_*.res" >> $R/tok_phases.otrun.log 2>&1
echo "$(date) phases done rc=$?" >> $R/tok_chain.log
