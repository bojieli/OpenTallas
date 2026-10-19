#!/bin/bash
# Install the local orphan reaper (ROOT-0100): ~/bin/ot-orphan-reaper + systemd --user timer (every 10 min).
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
install -m 755 "$D/ot_orphan_reaper.py" "$HOME/bin/ot-orphan-reaper"
mkdir -p "$HOME/.config/systemd/user"
install -m 644 "$D/systemd/ot-orphan-reaper.service" "$D/systemd/ot-orphan-reaper.timer" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now ot-orphan-reaper.timer
systemctl --user list-timers ot-orphan-reaper.timer --no-pager
