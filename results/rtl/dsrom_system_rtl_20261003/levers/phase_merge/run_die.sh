#!/bin/bash
# L0 TP-4 die-group runtime (original r4 archives + original driver), images ARM = off (original r3) | on (merged)
E=/srv/opentallas-scratch/claude/dsrom-system/levers/pm
ARM=$1
mkdir -p $E/die_$ARM
cd $E/die_$ARM
date -u +%Y-%m-%dT%H:%M:%SZ > start_utc
RT_WATCHDOG=${RT_WATCHDOG:-2000} RT_THREADS=${RT_THREADS:-16} /usr/bin/time -v $E/v41_die_rt $E/img_$ARM $E/die_$ARM 400000 > run.log 2>&1
echo "rc=$?" > rc
date -u +%Y-%m-%dT%H:%M:%SZ > end_utc
