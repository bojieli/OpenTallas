#!/bin/bash
# Fence control-loop SS screens (2026-10-04). Usage: screens.sh <round> <label> <screen args...>
R=/srv/opentallas-scratch/claude/hbm-fence-loop
rnd=$1; lab=$2; shift 2
O=$R/runs/$rnd; mkdir -p $O
cd $R/src
export OT_SCREEN_ROOT=$R/src
exec /srv/opentallas-scratch/admit.sh ${NEED:-6} -- python3 results/rtl/hbm_clock_loops_20261004/fence/screen.py --work $O/$lab --output $O/$lab.json --label $lab "$@" > $O/$lab.log 2>&1
