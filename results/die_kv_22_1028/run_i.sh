#!/bin/bash
# DIE-KV-22 step 2 iteration i = all-region DME, no pads, stage cal = own-leg refit of h (kv_cal_fit_h: 3712 legs, k2 > 0)
cd /srv/opentallas-scratch2/claude/die-kv-22-1028
A="--region-dme delay --region-dme-stage-cal $PWD/kv_cal_fit_h.json --region-dme-workers 16"
NOPAD=1 ./kit3.sh i $A > kit_i.log 2>&1; echo KIT_DONE $(date)
./chain3.sh i > chain_i.log 2>&1; echo CHAIN_DONE $(date)
sed -i "s#--tap-from kv_cal_fit_c.json --rep-um 150 --built-with kv_cal_fit_c.json#--tap-from kv_cal_fit_c.json --rep-um 150 --built-with \${BUILT:-kv_cal_fit_c.json}#" post.sh
BUILT=kv_cal_fit_h.json ./post.sh i > post_i.log 2>&1; echo POST_DONE $(date)
