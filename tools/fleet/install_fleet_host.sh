#!/bin/bash
# install_fleet_host.sh (FLEET-NEW3 2026-10-24): make a fresh fleet host an ot-run target.  Run ON the host as the
# fleet user (ubuntu, passwordless sudo) from a copy of tools/fleet:
#   bash tools/fleet/install_fleet_host.sh [--role coord]
# Idempotent; never stops or signals a running job; helpers are replaced atomically (install -> new inode).
#  1. scratch: /srv/opentallas-scratch (real dir on the host's biggest filesystem, owned by the user) with claude/ and
#     the convenience symlink ~/ot-scratch -> /srv/opentallas-scratch.  An existing mount or directory is kept.
#  2. ot-heavy helpers: /usr/local/bin/{ot-heavy,ot-heavy-reconcile}, /usr/local/lib/ot-heavy/{ot-heavy-exit,bin/docker},
#     then the repo installers for ot-vl-jcap (VL_JCAP_1022), ot-protect-die (DIE_WATCHDOG_1021) and OOMADJ_999_1022.
#  3. earlyoom (install_host_guard.sh arguments), /etc/ot-heavy.conf (coord role: MIN_AVAIL_FRAC=0.15 so the agents on the
#     coordinator keep >= 15 % of RAM), user linger (the systemd --user manager that owns the oth-* scopes survives the
#     ssh session), and a user crontab line running ot-heavy-reconcile every 2 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
role=${2:-normal}; [ "${1:-}" = --role ] || role=normal
u=$(id -un)

# 1. scratch
if [ ! -e /srv/opentallas-scratch ]; then
  sudo -n mkdir -p /srv/opentallas-scratch
  sudo -n chown "$u:$u" /srv/opentallas-scratch
fi
mkdir -p /srv/opentallas-scratch/claude
[ -e "$HOME/ot-scratch" ] || ln -s /srv/opentallas-scratch "$HOME/ot-scratch"

# 2. helpers
sudo -n install -d -m 0755 /usr/local/lib/ot-heavy /usr/local/lib/ot-heavy/bin
sudo -n install -d -m 1777 /var/tmp/ot-heavy
sudo -n install -m 0755 "$here/ot-heavy" /usr/local/bin/ot-heavy
sudo -n install -m 0755 "$here/ot-heavy-reconcile" /usr/local/bin/ot-heavy-reconcile
sudo -n install -m 0755 "$here/ot-heavy-exit" /usr/local/lib/ot-heavy/ot-heavy-exit
sudo -n install -m 0755 "$here/ot-heavy-docker" /usr/local/lib/ot-heavy/bin/docker
sudo -n python3 "$here/install_vl_jcap.py" "$here/ot-vl-jcap" >/dev/null
sudo -n python3 "$here/install_die_protection.py" >/dev/null
sudo -n python3 "$here/install_oomadj_999.py" >/dev/null

# 3. host guard, config, linger, cron
command -v earlyoom >/dev/null || sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q earlyoom >/dev/null
echo 'EARLYOOM_ARGS="-m 3,2 -s 100,100 -r 300 -n --prefer ^(verilator_bin|verilator_bin_dbg|cc1plus|cc1|g\+\+|c\+\+|clang\+\+|ld|yosys|yosys-abc)$ --avoid ^(sshd|systemd|systemd-journal|dockerd|containerd|containerd-shim.*|sudo|bash)$"' \
  | sudo -n tee /etc/default/earlyoom >/dev/null
sudo -n systemctl enable earlyoom >/dev/null 2>&1
sudo -n systemctl restart earlyoom
if [ ! -f /etc/ot-heavy.conf ]; then
  { echo "# ot-heavy admission factors (see ot-heavy-reconcile header); FLEET-NEW3 2026-10-24"
    if [ "$role" = coord ]; then echo "MIN_AVAIL_FRAC=0.15"; fi; } | sudo -n tee /etc/ot-heavy.conf >/dev/null
fi
sudo -n loginctl enable-linger "$u"
line='*/2 * * * * /usr/local/bin/ot-heavy-reconcile >/dev/null 2>&1'
{ crontab -l 2>/dev/null | grep -vF '/usr/local/bin/ot-heavy-reconcile' || true; echo "$line"; } | crontab -
echo "FLEET_HOST_OK $(hostname) role=$role scratch=$(df -BG --output=avail /srv/opentallas-scratch | tail -1 | tr -d ' ') free" \
  "earlyoom=$(systemctl is-active earlyoom) die-protection=$(systemctl is-active ot-die-protection 2>/dev/null)" \
  "linger=$(loginctl show-user "$u" -p Linger --value) reconcile=$(/usr/local/bin/ot-heavy-reconcile --free / | head -c 80)"
