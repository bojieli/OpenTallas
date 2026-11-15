#!/bin/bash
# usage: install_noprog_watchdog.sh [--no-enable] HOST...   (run from the repo's tools/autopilot; HOST=local installs here)
# Deploy by copy + mv (nothing is patched in place), same file on every host.  Timer is enabled unless --no-enable.
set -e
D=$(cd "$(dirname "$0")" && pwd); EN=1; [ "$1" = --no-enable ] && { EN=0; shift; }
for h in "$@"; do
  if [ "$h" = local ]; then R="bash -c"; CP() { cp "$1" "$HOME/$2"; }; else R="ssh -n -o ControlPath=none $h"; CP() { scp -q -o ControlPath=none "$1" "$h:$2"; }; fi
  CP "$D/noprog_watchdog.py" '.local/bin/ot-noprog-watchdog.new'
  CP "$D/systemd/noprog.service" '.config/systemd/user/noprog.service.new'
  CP "$D/systemd/noprog.timer" '.config/systemd/user/noprog.timer.new'
  $R "set -e; cd ~; chmod 755 .local/bin/ot-noprog-watchdog.new; mv .local/bin/ot-noprog-watchdog.new .local/bin/ot-noprog-watchdog; mv .config/systemd/user/noprog.service.new .config/systemd/user/noprog.service; mv .config/systemd/user/noprog.timer.new .config/systemd/user/noprog.timer; mkdir -p .local/state/noprog/policy; export XDG_RUNTIME_DIR=/run/user/\$(id -u); systemctl --user daemon-reload; [ $EN = 1 ] && systemctl --user enable --now noprog.timer || true; echo $h installed"
done
