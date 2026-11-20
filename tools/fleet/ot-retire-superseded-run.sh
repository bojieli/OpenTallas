#!/bin/bash
# ot-retire-superseded-run (FLEET-OPS-R): hourly, every host.  Pulls the hub kit_wave.json and runs retire_superseded.py --apply, which
# retires every dies.<die>.superseded_trees tree that exists on THIS host, whole, through ot_delete_guard (fail closed: a missing or
# older-than-6h protected list, or a missing guard module, retires nothing).  Log: ~/.local/state/ot-retire-superseded/log.jsonl
set -u
C=/srv/opentallas-scratch2/claude
RT=$C/rt/current/tools/autopilot/retire_superseded.py     # installed tools tree only (DISK-AUTOPRUNE-REINSTALL-1119: the lane folder clean-all-1115 was deleted)
G=$C/rt/current/tools/fleet/ot_delete_guard.py
L=$HOME/.local/state/ot-delete-guard/protected.txt
D=$HOME/.local/state/ot-retire-superseded; mkdir -p "$D"
[ -f "$RT" ] && [ -f "$G" ] && [ -f "$L" ] || { echo "missing tool/guard/list: nothing retired" >&2; exit 3; }
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
if [ "$(hostname -s)" = tolerant-swine ]; then cp $C/hub-coord/autopilot/kit_wave.json "$W/kw.json" || exit 3
else scp -q -o BatchMode=yes -o ConnectTimeout=15 -o ControlPath=none intel2:$C/hub-coord/autopilot/kit_wave.json "$W/kw.json" || exit 3; fi
exec python3 -I "$RT" --kit-wave "$W/kw.json" --guard-module "$G" --list "$L" --log "$D/log.jsonl" --apply
