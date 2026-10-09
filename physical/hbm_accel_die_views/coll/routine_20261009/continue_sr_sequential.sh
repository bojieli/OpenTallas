#!/usr/bin/env bash
set -euo pipefail
jobdir=/srv/opentallas-scratch2/scratch/codex/hbm-collector-sr-dpl-inspect-20261009
# Lightweight observer only; no memory reservation until actual predecessor terminal.
mkdir "$jobdir/bounded-sequential-owner.lock" || { echo 'SR_DUPLICATE_SEQUENCE_REJECTED';exit 1; }
if test -e "$jobdir/sr-bounded-release181.log"; then echo 'SR_EXISTING_BOUND_ARTIFACT_REJECTED';exit 1;fi
while test -r /proc/1753201/comm && test "$(cat /proc/1753201/comm)" = openroad; do sleep 30;done
printf '%s\n' 'SR_WIDER_PREDECESSOR_TERMINAL'
sha256sum "$jobdir/probe_sr_bounded_release181.tcl" "$jobdir/run_probe_sr_bounded.sh"
# 32GiB is conservative phase-derived above actual old DPL22.6GiB; no hard process cap.
/srv/opentallas-scratch/admit.sh 32 -- bash "$jobdir/run_probe_sr_bounded.sh"
