#!/bin/bash
# hourly: regenerate lanes/LIVE-LANES.tsv from post activity (lane live = posted within 6 h, or named in live_spec.tsv) and commit it
export PATH=$HOME/.local/bin:/usr/local/bin:$PATH
S2=/srv/opentallas-scratch2/claude; B=$S2/CLASS-TRACK; C=$HOME/coord
python3 -I $B/wt/tools/class_track/live_lanes.py build --spec $B/live_spec.tsv --dead-from $C/lanes/COORD-LANES-1125-2005.tsv --posts $C/lanes/posts --active-hours 6 --out $B/LIVE-LANES.new --dead-out $B/DEAD-LANES.new || exit 1
cp $B/LIVE-LANES.new $C/lanes/LIVE-LANES.tsv; cp $B/DEAD-LANES.new $C/lanes/DEAD-LANES.tsv
cd $C && bash bin/coord-commit.sh "CLASS-TRACK hourly LIVE-LANES refresh" lanes/LIVE-LANES.tsv lanes/DEAD-LANES.tsv 2>&1 | tail -1
