#!/bin/bash
# Fleet host guard (2026-10-10, EPYC2/3/4 memory-exhaustion hangs). Run ON a host with sudo:
#   bash install_host_guard.sh <path-to-ot-heavy>
# 1. /usr/local/bin/ot-heavy + /etc/ot-heavy.conf (BIG_SLOTS=2 large builds per host, SMALL_SLOTS=8)
# 2. earlyoom: SIGTERM at 3 % / SIGKILL at 2 % available RAM, prefers verilator / cc1plus / C++ / sims, never sshd /
#    systemd / dockerd / containerd; honours oom_score_adj (die runs at -900 stay protected)
set -e
src=${1:?ot-heavy path}
sudo -n install -m 0755 "$src" /usr/local/bin/ot-heavy
[ -f /etc/ot-heavy.conf ] || echo -e "BIG_SLOTS=2\nSMALL_SLOTS=8" | sudo -n tee /etc/ot-heavy.conf >/dev/null
command -v earlyoom >/dev/null || sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q earlyoom >/dev/null
echo 'EARLYOOM_ARGS="-m 3,2 -s 100,100 -r 300 -n --prefer ^(verilator_bin|verilator|cc1plus|cc1|g\+\+|c\+\+|clang\+\+|ld|vvp|iverilog|python3)$ --avoid ^(sshd|systemd|systemd-journal|dockerd|containerd|containerd-shim.*|sudo|bash)$"' | sudo -n tee /etc/default/earlyoom >/dev/null
sudo -n systemctl enable --now earlyoom >/dev/null 2>&1
sudo -n systemctl restart earlyoom
echo "HOST_GUARD_OK $(hostname) earlyoom=$(systemctl is-active earlyoom) ot-heavy=$(command -v ot-heavy) $(cat /etc/ot-heavy.conf | tr '\n' ' ')"
