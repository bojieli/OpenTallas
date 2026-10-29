#!/bin/bash
set -u
R=/srv/opentallas-scratch2/claude/codex-flow-hold-0830
mkdir -p "$R/s81_rc/rc"
cp /srv/opentallas-scratch2/claude/ce10-cfg-route-1029/kit/setRC_rcx.tcl "$R/s81_rc/rc/current.tcl"
bash "$R/rc_calib_run.sh" /srv/opentallas-scratch2/claude/ce10-cfg-route-1029/kit/signoff "$R/s81_rc" M2-M7 16 "rcx_ff est_ff" > "$R/s81_rc/run.log" 2>&1
echo s81 RC_EXIT=$?
mkdir -p "$R/head_rc/rc"
cp /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_a4453d400_1029_072115_215640/gen/hd_turn_a/setRC_rcx.tcl "$R/head_rc/rc/current.tcl"
bash "$R/rc_calib_run.sh" /srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_a4453d400_1029_072115_215640/gen/hd_turn_a/signoff "$R/head_rc" M2-M7 16 "rcx_ff est_ff" > "$R/head_rc/run.log" 2>&1
echo head RC_EXIT=$?
mkdir -p "$R/hbm_rc/rc"
cp /srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/kit/setRC_rcx.tcl "$R/hbm_rc/rc/current.tcl"
bash "$R/rc_calib_run.sh" /srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/kit/signoff "$R/hbm_rc" M2-M7 16 "rcx_ff est_ff" > "$R/hbm_rc/run.log" 2>&1
echo hbm RC_EXIT=$?
