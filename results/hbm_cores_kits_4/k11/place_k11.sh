#!/bin/bash
B=/srv/opentallas-scratch2/claude/hbm-cores-kits-4
for K in $B/k11/kits/*-_k11; do n=$(basename $K); grep -q "KIT_PREFLIGHT PASS" $B/k11/preflight/$n.txt || { echo "$n preflight not PASS"; continue; }
  case $n in *qcore_r13*) M=24; T=8;; *serdes*|*calendar*) M=32; T=16;; *) M=40; T=16;; esac
  ssh -o ControlPath=none epyc2 "mkdir -p $K" && rsync -a $K/ epyc2:$K/ && ~/.local/bin/ot-run --mem $M --threads $T --hosts epyc2 --dir $K -- bash $K/run_kit_hbm.sh $K place $M $T > $B/otrun/$n.place.otrun.log 2>&1 &
done; wait
