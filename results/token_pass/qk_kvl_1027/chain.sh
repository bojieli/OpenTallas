#!/bin/bash
# TOK-QK-KVL: when the per-layer build has landed AND the real-history vectors exist (vec_real/.done, COORD 10-27:
# the verdict uses the real prefill history), launch the 12 sims (launch_all.sh) on vec_real.
K=/srv/opentallas-scratch2/claude/tok-qk-kvl
until grep -q 'ot-run: RAN' $K/otrun_build.log && [ -e $K/vec_real/.done -o -e $K/vec_real/.failed ]; do sleep 60; done
if grep -q 'exit 0' $K/otrun_build.log && [ -x $K/build/obj/Vtb_kvslice ] && [ -e $K/vec_real/.done ]; then
  echo "LAUNCH vec_real $(date -Is)" > $K/chain.log; $K/launch_all.sh 24 localhost $K/vec_real >> $K/chain.log 2>&1
else echo "NOT_LAUNCHED build/vec_real failed $(date -Is)" > $K/chain.log; fi
