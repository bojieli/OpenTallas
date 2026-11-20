#!/bin/bash
# ot-disk-autoprune-run (DISK-AUTOPRUNE-REINSTALL-1119, COORD / FABLE-FLOW-1355 item 4): disk-refusal auto-prune wrapper, formerly clean-all-1115/autoprune-run.sh (a lane folder that was deleted:
# the unit then failed with 203/EXEC every 10 min on intel1 and epyc2).  Now it lives in the installed tools tree (rt/current), with every helper next to it.
# Cheap free-space check first; only below AUTOPRUNE_BELOW (65 GB) it pulls the hub markers, builds the text refs and the provenance refs on the hub, and runs
# ot_disk_autoprune.py trigger with every guard (ot-delete guard, refs, markers).  AUTOPRUNE_MODE=plan makes it print the plan only (no delete) and AUTOPRUNE_BELOW=N overrides the threshold (verification).
T=/srv/opentallas-scratch2/claude/rt/current/tools/fleet
S=$HOME/.local/state/ot-disk-autoprune; mkdir -p $S
free=$(df -BG --output=avail /srv/opentallas-scratch2 | tail -1 | tr -dc 0-9)
[ "${free:-0}" -ge "${AUTOPRUNE_BELOW:-65}" ] && { echo "free ${free} GB >= ${AUTOPRUNE_BELOW:-65}: nothing to do" | logger -t ot-disk-autoprune; exit 0; }
W=$(mktemp -d); trap 'rm -rf $W' EXIT
H=intel2; HC=/srv/opentallas-scratch2/claude/hub-coord
mkdir -p $W/mk
if [ "$(hostname -s)" = tolerant-swine ]; then
  cp $HC/lanes/handoff/tree_switch_*.json $W/mk/ 2>/dev/null
  python3 -I $T/ot_cleanup_textrefs.py $HC $HC/lanes/handoff $W/text.refs $W/keepn >/dev/null
  python3 -I $T/ot_cleanup_provrefs.py /srv/opentallas-scratch2/claude/rt/current $W/provrefs.txt $HC/autopilot/kit_wave.json >/dev/null 2>&1 || : > $W/provrefs.txt
else
  scp -q -o ConnectTimeout=15 -o BatchMode=yes $H:$HC/lanes/handoff/tree_switch_*.json $W/mk/ || exit 3
  ssh -o ConnectTimeout=15 -o BatchMode=yes $H "python3 -I $T/ot_cleanup_textrefs.py $HC $HC/lanes/handoff /tmp/ap_text.refs /tmp/ap_keepn; python3 -I $T/ot_cleanup_provrefs.py /srv/opentallas-scratch2/claude/rt/current /tmp/ap_provrefs.txt $HC/autopilot/kit_wave.json" >/dev/null 2>&1 || exit 3
  scp -q -o ConnectTimeout=15 -o BatchMode=yes $H:/tmp/ap_text.refs $W/text.refs || exit 3
  scp -q -o ConnectTimeout=15 -o BatchMode=yes $H:/tmp/ap_provrefs.txt $W/provrefs.txt 2>/dev/null || : > $W/provrefs.txt
fi
python3 -I $T/ot_cleanup_refguard.py $W/refguard.tsv >/dev/null 2>&1
MODE=${AUTOPRUNE_MODE:-trigger}
python3 -I $T/ot_disk_autoprune.py $MODE --markers $W/mk --refs $W/provrefs.txt $W/refguard.tsv --text-refs $W/text.refs --root /srv/opentallas-scratch2/claude/kw45 2>&1 | logger -t ot-disk-autoprune
exit ${PIPESTATUS[0]}
