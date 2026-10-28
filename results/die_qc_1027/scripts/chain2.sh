#!/bin/bash
set -u
D=/srv/opentallas-scratch2/claude/die-qc-1027
rm -rf $D/trial $D/out_TT $D/out_FF $D/clk
mv $D/chain.log $D/chain_try1.log 2>/dev/null
bash $D/chain.sh && bash $D/post.sh
