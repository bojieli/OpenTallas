#!/bin/bash
# TOK-QK-KVL: when the per-layer build lands, launch the 12 sims (launch_all.sh); record the outcome.
K=/srv/opentallas-scratch2/claude/tok-qk-kvl
until grep -q 'ot-run: RAN' $K/otrun_build.log; do sleep 60; done
if grep -q 'exit 0' $K/otrun_build.log && [ -x $K/build/obj/Vtb_kvslice ]; then
  echo "LAUNCH $(date -Is)" > $K/chain.log; $K/launch_all.sh 24 localhost >> $K/chain.log 2>&1
else echo "BUILD_FAILED $(date -Is)" > $K/chain.log; fi
