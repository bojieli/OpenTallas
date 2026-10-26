#!/bin/bash
# TOK-DS-6: build tb_dsdv_idx_rg3 variants (base, MUT3, probe DQR48/IQD1024) for the k=3 shard bench + param probe.
W=/srv/opentallas-scratch2/claude/wt/tok-ds-6-1026
RB=/srv/opentallas-scratch2/claude/tok-ds-6-1026/rb
cd $W
bash rtl/dsrom_sys/s81_dv/idx/test/idxrd3_campaign.sh $RB "$1" "$2" 1
