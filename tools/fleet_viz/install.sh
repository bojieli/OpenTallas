#!/usr/bin/env bash
# Install tools/fleet_viz into ~/.local/share/fleet-viz and (re)start the user service.
set -euo pipefail
src=$(cd "$(dirname "$0")" && pwd); dst=$HOME/.local/share/fleet-viz
mkdir -p "$dst" "$HOME/.config/systemd/user"
cp "$src"/{server.py,agent.py,recorder.py,export_replay.py,index.html,fleet_hosts.json} "$dst"/
cp "$src"/fleet-viz.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable fleet-viz.service >/dev/null
systemctl --user restart fleet-viz.service
rm -f "$dst"/landmask.js
