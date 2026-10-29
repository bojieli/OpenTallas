#!/bin/bash
set -u
R=/srv/opentallas-scratch2/claude/codex-flow-hold-0830
mkdir -p "$R/kv_rc/rc"
cp /srv/opentallas-scratch2/claude/flow-hold-3-v1/q3/setRC_rcx.tcl "$R/kv_rc/rc/current.tcl"
bash "$R/rc_calib_run.sh" /srv/opentallas-scratch2/claude/flow-hold-3-v1/q3/signoff "$R/kv_rc" M2-M7 16 "rcx_ff est_ff" > "$R/kv_rc/run.log" 2>&1
echo kv RC_EXIT=$?
mkdir -p "$R/qc_rc/rc"
cp /srv/opentallas-scratch2/claude/codex-qc-btab-0251/kits_route_compat/qfd_dv_s8x_btab_turntree/setRC_rcx.tcl "$R/qc_rc/rc/current.tcl"
bash "$R/rc_calib_run.sh" /srv/opentallas-scratch2/claude/codex-qc-btab-0251/kits_route_compat/qfd_dv_s8x_btab_turntree/signoff "$R/qc_rc" M2-M7 16 "rcx_ff est_ff" > "$R/qc_rc/run.log" 2>&1
echo qc RC_EXIT=$?
