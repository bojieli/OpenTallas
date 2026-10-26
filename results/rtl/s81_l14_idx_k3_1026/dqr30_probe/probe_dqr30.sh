#!/bin/bash
# TOK-DS-6 step 3 (param-only, no RTL edit): rg3 at DQR 30 (max legal: DQR/RFD <= 31, even) + IQD 1024, 43,691 keys.
# Waits for the dqr30 build, then runs P=2 and P=3 (control) synthetic scans.  Results: rb/dqr30/x_*.res
R=/srv/opentallas-scratch2/claude/tok-ds-6-1026/rb
until [ -x $R/dqr30/obj/Vtb_dsdv_idx_rg3 ]; do sleep 30; done
cd /srv/opentallas-scratch2/claude/wt/tok-ds-6-1026
bash rtl/dsrom_sys/s81_dv/idx/test/idxrd3_campaign.sh $R dqr30 "-GMUT=0 -GDQR=30 -GIQD=1024" 3 \
  "x_p2_43691|+N=43691 +P=2 +T0=400" "x_p2_43691_t900|+N=43691 +P=2 +T0=900" "x_p3_43691|+N=43691 +P=3 +T0=400"
cat $R/dqr30/x_*.res > $R/dqr30/PROBE_DONE
