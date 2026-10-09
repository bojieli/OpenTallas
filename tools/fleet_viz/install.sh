#!/usr/bin/env bash
# Install tools/fleet_viz into ~/.local/share/fleet-viz and (re)start the user service.
set -euo pipefail
src=$(cd "$(dirname "$0")" && pwd); dst=$HOME/.local/share/fleet-viz
mkdir -p "$dst" "$HOME/.config/systemd/user"
cp "$src"/{server.py,agent.py,recorder.py,elements.py,export_replay.py,index.html,fleet_hosts.json} "$dst"/
cp "$src"/{coverage.py,explorer.py,explorer_geom.py,explorer.html,explorer.js,explorer_story.js,explorer_dies.json,explorer_names.json,explorer_compose.json,stories_import.py} "$dst"/
mkdir -p "$dst/stories" "$dst/explorer"
cp "$src"/stories/*.json "$dst/stories/"
rm -rf "$dst/explorer/token"; cp -r "$src/explorer/token" "$dst/explorer/token"
rm -rf "$dst/explorer/coverage"; cp -r "$src/explorer/coverage" "$dst/explorer/coverage"
cp "$src"/fleet-viz.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable fleet-viz.service >/dev/null
systemctl --user restart fleet-viz.service
rm -f "$dst"/landmask.js
