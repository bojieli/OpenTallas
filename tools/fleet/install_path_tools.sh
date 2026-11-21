#!/bin/bash
# install_path_tools.sh (FLEET-OPS-R, COORD 11-17): put ot-delete and ot-gate-remote on PATH (~/.local/bin, where ot-run lives) of THIS host as
# symlinks into rt/current/tools/fleet, so a later rt/current switch updates them.  Idempotent; prints one line per tool.
set -u
R=${OT_RT:-/srv/opentallas-scratch2/claude/rt/current}/tools/fleet; B=${OT_BIN:-$HOME/.local/bin}; mkdir -p "$B"
for t in ot-delete ot-gate-remote ot-lane-clone ot-docker-prune ot-wait; do
  if [ -f "$R/$t" ]; then ln -sfn "$R/$t" "$B/$t"; echo "$(hostname) $t -> $(readlink "$B/$t")"; else echo "$(hostname) $t MISSING in $R"; fi
done
[ -f "$R/ot_status.py" ] || echo "$(hostname) WARNING ot_status.py missing in $R (ot-wait needs it)"
[ -f "$R/ot_delete_guard.py" ] || echo "$(hostname) WARNING ot_delete_guard.py missing in $R"
