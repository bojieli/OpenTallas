#!/bin/bash
# S81-L20RD2 bench campaign 1 (base build MUT=0): run from the lane src dir
cd /srv/opentallas-scratch/claude/s81-l20rd2-1020/src
bash rtl/dsrom_sys/s81_dv/idx/test/idxrd2_campaign.sh /srv/opentallas-scratch/claude/s81-l20rd2-1020/out b1 "-GMUT=0 -GSRAM_MACRO=1" 12 \
 "pass_small|+N=4096 +B=13 +T0=400 +P=3" \
 "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3" \
 "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" \
 "pass_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" \
 "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" \
 "pass_l2|+N=43691 +B=13 +T0=400 +P=3" \
 "pass_l20|+N=87382 +B=13 +T0=400 +P=3" \
 "fail_late|+N=4096 +B=13 +T0=60 +P=3" \
 "x_t0_250|+N=4096 +B=13 +T0=250 +P=3" \
 "x_t0_300|+N=4096 +B=13 +T0=300 +P=3" \
 "x_t0_350|+N=4096 +B=13 +T0=350 +P=3" \
 "x_p2|+N=4096 +B=13 +T0=400 +P=2"
