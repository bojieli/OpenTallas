#!/bin/bash
# usage: install_noprog_stage.sh [--no-enable]      (run on the hub from the repo's tools/autopilot; installs the advisor timer there only)
# The other hosts need nothing: `hub` pushes both files to ~/.local/lib/noprog on every host each run (copy + mv, never patched in place).
set -e
D=$(cd "$(dirname "$0")" && pwd); EN=1; [ "$1" = --no-enable ] && EN=0
mkdir -p ~/.local/lib/noprog ~/.config/systemd/user ~/.local/state/noprog
for f in noprog_watchdog.py noprog_stage.py; do cp "$D/$f" ~/.local/lib/noprog/$f.new; mv ~/.local/lib/noprog/$f.new ~/.local/lib/noprog/$f; done
for f in noprog-stage.service noprog-stage.timer; do cp "$D/systemd/$f" ~/.config/systemd/user/$f.new; mv ~/.config/systemd/user/$f.new ~/.config/systemd/user/$f; done
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user daemon-reload
[ $EN = 1 ] && systemctl --user enable --now noprog-stage.timer || true
echo "noprog-stage installed (enabled=$EN)"
