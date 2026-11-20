#!/bin/bash
# install_store_gc.sh (STORE-GC-HOURLY-1120): the user timer ot-store-gc on THIS host (every gen host and the hub), from rt/current.  Undo: systemctl --user disable --now ot-store-gc.timer
set -eu
T=${SG_TOOLS:-/srv/opentallas-scratch2/claude/rt/current/tools/fleet}
[ -f "$T/systemd/ot-store-gc.timer" ] && [ -f "$T/ot-store-gc-run.sh" ] || { echo "rt/current has no ot-store-gc units: sync first" >&2; exit 3; }
mkdir -p ~/.config/systemd/user ~/.local/state/ot-store-gc
for f in ot-store-gc.service ot-store-gc.timer; do cp "$T/systemd/$f" ~/.config/systemd/user/$f.new && mv -f ~/.config/systemd/user/$f.new ~/.config/systemd/user/$f; done
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user daemon-reload
systemctl --user enable --now ot-store-gc.timer
echo "$(hostname -s): store GC timer $(systemctl --user is-active ot-store-gc.timer), next: $(systemctl --user list-timers ot-store-gc.timer --no-legend | awk '{print $1, $2, $3}')"
