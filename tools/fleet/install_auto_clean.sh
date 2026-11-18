#!/bin/bash
# install_auto_clean.sh (FLEET-OPS-R, OWNER 11-18): the user timer ot-auto-clean on THIS build host (intel1 epyc2 epyc7 epyc8 epyc9 epyc10), from rt/current.  Never on the hub / localhost.
# Undo: systemctl --user disable --now ot-auto-clean.timer
set -eu
case "$(hostname -s)" in
  tolerant-swine|ubuntu|intel2|localhost|rtx-pro) echo "install_auto_clean: REFUSED on $(hostname -s): build hosts only (intel1 epyc2 epyc7 epyc8 epyc9 epyc10)" >&2; exit 64;;
esac
T=${AC_TOOLS:-/srv/opentallas-scratch2/claude/rt/current/tools/fleet}
[ -f "$T/systemd/ot-auto-clean.timer" ] && [ -x "$T/ot-auto-retire-run.sh" -o -f "$T/ot-auto-retire-run.sh" ] || { echo "rt/current has no ot-auto-clean units: sync first" >&2; exit 3; }
mkdir -p ~/.config/systemd/user ~/.local/state/auto-clean
for f in ot-auto-clean.service ot-auto-clean.timer; do cp "$T/systemd/$f" ~/.config/systemd/user/$f.new && mv -f ~/.config/systemd/user/$f.new ~/.config/systemd/user/$f; done
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user daemon-reload
systemctl --user enable --now ot-auto-clean.timer
echo "$(hostname -s): timer $(systemctl --user is-active ot-auto-clean.timer), next: $(systemctl --user list-timers ot-auto-clean.timer --no-legend | awk '{print $1, $2, $3}')"
