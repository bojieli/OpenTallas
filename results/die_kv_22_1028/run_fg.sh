#!/bin/bash
# DIE-KV-22 step 2: ALL 128 KV regions as fitted DME delay trees (stage cal = DIE-KV-21 kv_cal_fit_c, own-leg refit of tree c), one event.
# f = with KV-20 phy tap pads; g = no tap pads (DME balances the phy tap itself).
cd /srv/opentallas-scratch2/claude/die-kv-22-1028
A="--region-dme delay --region-dme-stage-cal $PWD/kv_cal_fit_c.json --region-dme-workers 16"
./kit3.sh f $A > kit_f.log 2>&1 & NOPAD=1 ./kit3.sh g $A > kit_g.log 2>&1 & wait
echo KIT_DONE $(date)
./chain3.sh f > chain_f.log 2>&1 & ./chain3.sh g > chain_g.log 2>&1 & wait
echo CHAIN_DONE $(date)
