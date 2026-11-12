#!/bin/bash
bash /srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1plan/bind_rd1.sh > /srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1plan/run_rd1.out 2>&1 &
bash /srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1plan/ctl/bind_ctl.sh > /srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1plan/run_ctl.out 2>&1
wait
