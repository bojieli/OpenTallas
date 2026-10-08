#!/bin/bash
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin OT_SCRATCH=/srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/tmp OT_LV_CORE=w17
cd /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/src
date -u +%FT%TZ > /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/run/wf00.log
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/dsrom_lever_su_kr.py run --pregen /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr/img_k40 --sukr 40  --units he,me,su --single-only --output /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/run/wf00.json >> /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/run/wf00.log 2>&1
echo RC $? >> /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/run/wf00.log; date -u +%FT%TZ >> /srv/opentallas-scratch/claude/dsrom-system/levers/su_kr_w17/run/wf00.log
