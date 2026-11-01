#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/codex-qc-su-trials
B=/srv/opentallas-scratch2/claude/codex-qc-su-trials
while read -r module pid kit; do
 python3 "$W/tools/autopilot/enqueue.py" --die qwen_compute --type "$module" --kit "intel2:$kit" --src codex/qc-su-trials-1101@2969e602396e74523bd0c46837db2ffbcfdbc225 --geom AUTO --geom-ref 'Absolute placement AUTO-GEOM after CTS; GRT50 scope only, no DRT' --mem 24 --cells 260000 --lane CODEX-QC-SU --goal grt --runner "$B/grt_only.sh" --threads 2 --mode trial
done < "$B/jobs.tsv"
