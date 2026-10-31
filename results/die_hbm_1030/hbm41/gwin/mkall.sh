#!/bin/bash
# DIE-HBM-41 windowed GRT probes: 4 y-windows x {d38s=q0f_d38r, d38a} x {0, 50} congestion iterations
cd $(dirname $0)
declare -A W=( [wA]="3101.76 3706.56" [wB]="2695.68 3153.6" [wC]="1045.44 1546.56" [wD]="3706.56 4320" )
for w in wA wB wC wD; do for v in d38s:d38r d38a:d38a; do for it in 0 50; do
  d=${w}_${v%%:*}_i$it; rm -rf $d; python3 mkwin.py ../../die-hbm-38/g2/q0f_${v##*:} $d ${W[$w]} $it > $d.mk.log && cp run.sh $d/
done; done; done
