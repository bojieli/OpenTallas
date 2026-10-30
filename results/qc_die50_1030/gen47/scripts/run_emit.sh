#!/bin/bash
# DIE-QC-50/gen47 (a): main start_stage_emit on the gen47 START bind (startplanP) + gen47 kit ctree; reset wave (bounded sync relays)
set -u
mkdir -p /srv/opentallas-scratch2/claude/die-qc-50/gen47/emitP
systemd-run --user --scope -q -p MemoryMax=48G python3 /srv/opentallas-scratch2/claude/wt/die-qc-50-gen47/tools/die_plan/start_stage_emit.py emit /srv/opentallas-scratch2/claude/die-qc-50/gen47/startplanP/bind.json /srv/opentallas-scratch2/claude/die-qc-50/gen47/proofP --ctree /srv/opentallas-scratch2/claude/die-qc-49/gen47k/kit/clock --plan /srv/opentallas-scratch2/claude/wt/die-qc-50-gen47/physical/die_plan/qwen_compute/plan_of_record/plan_qc49.json --path-encoding base36 --reset-wave --out /srv/opentallas-scratch2/claude/die-qc-50/gen47/emitP/emitted > /srv/opentallas-scratch2/claude/die-qc-50/gen47/emitP/run.log 2>&1
echo "rc=$? $(date)" > /srv/opentallas-scratch2/claude/die-qc-50/gen47/emitP/status
