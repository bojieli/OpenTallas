#!/bin/bash
# mtp-lead independent rerun (fresh prepare from the reduced checkpoint + gold token seq, then RTL) of the original
# MTP campaigns 14/15 (L14) and 19/20 (L19), deep order (MR-5), source 628000701 (ROLLBACK_RING_DYN default 1)
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
B=/srv/opentallas-scratch/claude/mtp-lead/camp-628000701; S=$B/src; T=$S/tools/mtp_exact_wavefront2.py; cd $S
for L in 14 19; do /usr/bin/time -v python3 $T prepare --scratch $B/p$L --gold $B/gold.json --order deep --source-layer $L --rollback-ring-dyn > $B/prep$L.log 2>&1 & done; wait
run() { tag=$1; shift; /srv/opentallas-scratch/admit.sh 24 -- /usr/bin/time -v python3 $T run "$@" --jobs 16 > $B/$tag.log 2>&1; echo "rc=$?" > $B/$tag.rc; }
run r_c14_pos --scratch $B/p14 --order deep --source-layer 14 --rollback-ring-dyn --wave 1 --ctrl wfc &
run r_c15_neg --scratch $B/p14 --order deep --source-layer 14 --rollback-ring-dyn --wave 0 --ctrl wf &
run r_c19_pos --scratch $B/p19 --order deep --source-layer 19 --rollback-ring-dyn --wave 1 --ctrl wfc &
run r_c20_neg --scratch $B/p19 --order deep --source-layer 19 --rollback-ring-dyn --wave 0 --ctrl wf &
run r_c14_default_pos --scratch $B/p14 --order deep --source-layer 14 --wave 1 --ctrl wfc &
wait
python3 $T record --scratch $B/p14 --order deep --source-layer 14 --rollback-ring-dyn --output $B/rec_l14_ringdyn.json > $B/r_rec14.log 2>&1
python3 $T record --scratch $B/p19 --order deep --source-layer 19 --rollback-ring-dyn --output $B/rec_l19_ringdyn.json > $B/r_rec19.log 2>&1
python3 $T record --scratch $B/p14 --order deep --source-layer 14 --output $B/rec_l14_default.json > $B/r_rec14d.log 2>&1
echo done > $B/ALL_DONE2
