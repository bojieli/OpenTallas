#!/usr/bin/env bash
# intel2: wait for the canon ot-run (pid $1), then run canon_post.sh on epyc2.
R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-9
while kill -0 $1 2>/dev/null; do sleep 120; done
ssh -o ControlPath=none epyc2 "bash $R/canon_post.sh" >> $R/canon_chain.log 2>&1
echo "$(date) canon_post rc=$?" >> $R/canon_chain.log
