#!/bin/bash
# DIE-KV-14 (c): fishbone feed build chain = DIE-KV-12 recipe (kit2 die_trial qc11 archive inv r150 -> GRT0 TT/FF + duty -> proof/lpo/ca_spice -> CA width+phase + main die_sta_related), tools = wt/die-kv-14 (main 013a + KV-13)
cd /srv/opentallas-scratch2/claude/die-kv-14-1028
./chain2.sh fb_inv_r150 inv 150 > chain_fb_inv_r150.log 2>&1 || { echo CHAIN_FAIL; exit 1; }
./ca.sh fb_inv_r150 > ca_fb_inv_r150.log 2>&1; echo ALL_DONE $(date)
