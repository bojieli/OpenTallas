#!/bin/bash
# L0 TP-4 die-group runtime (original r4 archives + original driver), images ARM = off (original r3) | on (merged)
E=/srv/opentallas-scratch/claude/dsrom-system/levers/pm
ARM=$1
mkdir -p $E/pcl_$ARM
cd $E/pcl_$ARM
date -u +%Y-%m-%dT%H:%M:%SZ > start_utc
RT_WATCHDOG=${RT_WATCHDOG:-2000} RT_THREADS=${RT_THREADS:-16} /usr/bin/time -v $E/v41_die_rt_pclog $E/img_$ARM $E/pcl_$ARM ${MAXC:-12700} > run.log 2>&1
echo "rc=$?" > rc
date -u +%Y-%m-%dT%H:%M:%SZ > end_utc
