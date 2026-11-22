#!/bin/bash
# install_path_tools.sh (FLEET-OPS-R, COORD 11-17): put ot-delete and ot-gate-remote on PATH (~/.local/bin, where ot-run lives) of THIS host as
# symlinks into rt/current/tools/fleet, so a later rt/current switch updates them.  Idempotent; prints one line per tool.
set -u
R=${OT_RT:-/srv/opentallas-scratch2/claude/rt/current}/tools/fleet; B=${OT_BIN:-$HOME/.local/bin}; mkdir -p "$B"
# FLOW-OPS-1300 item 14 (COORD 11-21: lanes on localhost/rtx-pro got "ot-wait: No such file or directory" and armed no waiter): a host without
# rt/current (the coordinator host has no /srv/opentallas-scratch2) gets an ot-wait FORWARDER to the hub, where the ot-run clients and their
# ot-status records live.  Same arguments, same output and exit status.
if [ ! -d "$R" ]; then
  H=${OT_WAIT_HUB:-intel2}
  cat > "$B/.ot-wait.$$" <<EOW
#!/bin/bash
# ot-wait forwarder (install_path_tools.sh, FLOW-OPS-1300 item 14): no rt/current on this host; the job records are on $H.
q=""; for x in "\$@"; do q="\$q \$(printf '%q' "\$x")"; done
exec ssh -o ControlPath=none -o BatchMode=yes -o ServerAliveInterval=60 \${OT_WAIT_HUB:-$H} "ot-wait\$q"
EOW
  chmod 755 "$B/.ot-wait.$$" && mv -f "$B/.ot-wait.$$" "$B/ot-wait" && echo "$(hostname) ot-wait -> forwarder to $H (no $R here)"
  exit 0
fi
for t in ot-delete ot-gate-remote ot-lane-clone ot-docker-prune ot-wait; do
  if [ -f "$R/$t" ]; then ln -sfn "$R/$t" "$B/$t"; echo "$(hostname) $t -> $(readlink "$B/$t")"; else echo "$(hostname) $t MISSING in $R"; fi
done
[ -f "$R/ot_status.py" ] || echo "$(hostname) WARNING ot_status.py missing in $R (ot-wait needs it)"
[ -f "$R/ot_delete_guard.py" ] || echo "$(hostname) WARNING ot_delete_guard.py missing in $R"
