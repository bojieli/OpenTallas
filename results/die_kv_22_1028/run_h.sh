#!/bin/bash
# DIE-KV-22 step 2 variant h = all-region DME, NO KV-20 phy tap pads (g failed on an arg bug, not run)
cd /srv/opentallas-scratch2/claude/die-kv-22-1028
A="--region-dme delay --region-dme-stage-cal $PWD/kv_cal_fit_c.json --region-dme-workers 16"
NOPAD=1 ./kit3.sh h $A > kit_h.log 2>&1; echo KIT_DONE $(date)
./chain3.sh h > chain_h.log 2>&1; echo CHAIN_DONE $(date)
