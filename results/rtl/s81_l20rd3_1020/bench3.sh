#!/bin/bash
# S81-L20RD3 bench builds (run from src3 on the fleet host): $1 = build name; Verilator 5.050 via idxrd2_campaign.sh
cd /srv/opentallas-scratch/claude/s81-l20rd3-1020/src3
C=rtl/dsrom_sys/s81_dv/idx/test/idxrd2_campaign.sh; O=/srv/opentallas-scratch/claude/s81-l20rd3-1020/out
case $1 in
b3) bash $C $O b3 "-GMUT=0 -GSRAM_MACRO=1" 16 \
 "pass_small|+N=4096 +B=13 +T0=400 +P=3" \
 "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3" \
 "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" \
 "pass_g2048s2|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=2" \
 "pass_g2048s3|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=3" \
 "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" \
 "closed_g2048p3s2|+GATHER=1 +N=2048 +T0=1500 +P=3 +SEED=2" \
 "closed_g2048t700|+GATHER=1 +N=2048 +T0=700 +P=3" \
 "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" \
 "pass_l2|+N=43691 +B=13 +T0=400 +P=3" \
 "pass_l20|+N=87382 +B=13 +T0=400 +P=3" \
 "pass_l20s2|+N=87382 +B=13 +T0=400 +P=3 +SEED=2" \
 "closed_late|+N=4096 +B=13 +T0=60 +P=3" \
 "closed_glate|+GATHER=1 +N=2048 +T0=60 +P=4" \
 "x_p2|+N=4096 +B=13 +T0=400 +P=2" ;;
h450) bash $C $O h450 "-GMUT=0 -GSRAM_MACRO=1 -GCKH_PS=450" 8 \
 "x_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" \
 "x_g2048p3s2|+GATHER=1 +N=2048 +T0=1500 +P=3 +SEED=2" \
 "x_g2048p2|+GATHER=1 +N=2048 +T0=1500 +P=2" \
 "x_l20p2|+N=87382 +B=13 +T0=400 +P=2" ;;
m1|m3|m4) bash $C $O $1 "-GMUT=${1#m} -GSRAM_MACRO=1" 4 "fail_small|+N=4096 +B=13 +T0=400 +P=3" "fail_g|+GATHER=1 +N=256 +T0=1500 +P=3" ;;
m2|m5) bash $C $O $1 "-GMUT=${1#m} -GSRAM_MACRO=1" 4 "fail_small|+N=4096 +B=13 +T0=400 +P=3" ;;
m6) bash $C $O m6 "-GMUT=6 -GSRAM_MACRO=1" 4 "fail_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" ;;
m7) bash $C $O m7 "-GMUT=7 -GSRAM_MACRO=1" 4 "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" "closed_g2048p3s2|+GATHER=1 +N=2048 +T0=1500 +P=3 +SEED=2" "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" ;;
esac
