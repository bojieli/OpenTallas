#!/bin/bash
# mtp-lead fork A: seed projection production slice gate (positive RP 8 + sequential-join mutant), admitted.
B=/srv/opentallas-scratch/claude/mtp-seedproj
cd $B/src || exit 1
TAG=${1:-r1}
mkdir -p $B/$TAG
( /srv/opentallas-scratch/admit.sh 8 -- python3 tools/dsrom_mtp_seed_proj.py gate --snapshot $B/snapshot --ref $B/ref --work $B/$TAG/pos --rp 8 --jobs 12 > $B/$TAG/pos.txt 2>&1; echo "rc=$?" >> $B/$TAG/pos.txt ) &
( /srv/opentallas-scratch/admit.sh 8 -- python3 tools/dsrom_mtp_seed_proj.py gate --snapshot $B/snapshot --ref $B/ref --work $B/$TAG/mut --rp 8 --jobs 12 --mut-join > $B/$TAG/mut.txt 2>&1; echo "rc=$?" >> $B/$TAG/mut.txt ) &
( /srv/opentallas-scratch/admit.sh 8 -- python3 tools/dsrom_mtp_seed_proj.py gate --snapshot $B/snapshot --ref $B/ref --work $B/$TAG/pos_rp1 --rp 1 --jobs 12 > $B/$TAG/pos_rp1.txt 2>&1; echo "rc=$?" >> $B/$TAG/pos_rp1.txt ) &
wait
echo done > $B/$TAG/DONE
