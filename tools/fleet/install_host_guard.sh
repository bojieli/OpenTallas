#!/bin/bash
# Fleet host guard (2026-10-10, EPYC2/3/4 memory-exhaustion hangs). Run ON a host with sudo:
#   bash install_host_guard.sh <path-to-ot-heavy>
# 1. /usr/local/bin/ot-heavy + /etc/ot-heavy.conf (BIG_SLOTS=2 large builds per host, SMALL_SLOTS=8)
# 2. earlyoom: SIGTERM at 3 % / SIGKILL at 2 % available RAM, prefers verilator / cc1plus / C++ / yosys builds (not sims / python3), never sshd /
#    systemd / dockerd / containerd; honours oom_score_adj (die runs at -900 stay protected)
set -e
src=${1:?ot-heavy path}
sudo -n install -m 0755 "$src" /usr/local/bin/ot-heavy
[ -f /etc/ot-heavy.conf ] || echo -e "BIG_SLOTS=2\nSMALL_SLOTS=8" | sudo -n tee /etc/ot-heavy.conf >/dev/null
command -v earlyoom >/dev/null || sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q earlyoom >/dev/null
# FLEET-OOM 2026-10-18: vvp / iverilog / python3 are OFF the prefer list (at 3 % free earlyoom took 34 small benches and
# route python3s -- 9 MiB vvp at oom_score 1300 -- before the 100-300 GB cc1plus builds); the big builds (cc1plus,
# verilator_bin, yosys) are preferred, and the closure-loop runner raises a build to oom_score_adj 900 once its stage
# passes its declared GB.  Loop bench / route stages run at oom_score_adj 0.
# EARLYOOM_OPENROAD_1114 (ADMIT-TUNE-1): openroad is neither --prefer nor --avoid (--avoid openroad on 11-14 moved the kills to 27 docker/docker.real client processes on epyc9 in 4 min = 27 lost jobs); python/ssh-agent/dbus/find/git/grep are collateral
echo 'EARLYOOM_ARGS="-m 3,2 -s 100,100 -r 300 -n --prefer ^(verilator_bin|verilator_bin_dbg|cc1plus|cc1|g\+\+|c\+\+|clang\+\+|ld)$ --avoid ^(python3|python|ssh-agent|dbus-daemon|find|git|grep|sshd|systemd|systemd-journal|dockerd|containerd|containerd-shim.*|sudo|bash)$"' | sudo -n tee /etc/default/earlyoom >/dev/null
sudo -n systemctl enable --now earlyoom >/dev/null 2>&1
sudo -n systemctl restart earlyoom
# OOMAGE_1114 (ADMIT-TUNE-1): ot-oom-age lowers build processes' oom_score_adj with age (800 new, -100/h, floor 0) so earlyoom / the kernel
# kill the youngest first; root timer every 2 min.
sudo -n install -m 755 "$(dirname "$0")/ot-oom-age" /usr/local/bin/ot-oom-age
printf '[Unit]\nDescription=ot-oom-age\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/ot-oom-age\n' | sudo -n tee /etc/systemd/system/ot-oom-age.service >/dev/null
printf '[Unit]\nDescription=ot-oom-age every 2 min\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec=2min\nAccuracySec=10s\n[Install]\nWantedBy=timers.target\n' | sudo -n tee /etc/systemd/system/ot-oom-age.timer >/dev/null
sudo -n systemctl daemon-reload; sudo -n systemctl enable --now ot-oom-age.timer >/dev/null 2>&1
# MEMGROW_1114 (ADMIT-TUNE-1): ot-mem-grow raises a build container docker cap by 50 percent (max 2x the request) when it is above 85 percent and the host
# can pay for it, every minute (cap kills at 28.7 of 32 GB on slice_station t28/t30/t8).
sudo -n install -m 755 "$(dirname "$0")/ot-mem-grow" /usr/local/bin/ot-mem-grow
printf '[Unit]\nDescription=ot-mem-grow\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/ot-mem-grow\n' | sudo -n tee /etc/systemd/system/ot-mem-grow.service >/dev/null
printf '[Unit]\nDescription=ot-mem-grow every minute\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec=1min\nAccuracySec=5s\n[Install]\nWantedBy=timers.target\n' | sudo -n tee /etc/systemd/system/ot-mem-grow.timer >/dev/null
sudo -n systemctl daemon-reload; sudo -n systemctl enable --now ot-mem-grow.timer >/dev/null 2>&1
echo "HOST_GUARD_OK $(hostname) earlyoom=$(systemctl is-active earlyoom) ot-heavy=$(command -v ot-heavy) $(cat /etc/ot-heavy.conf | tr '\n' ' ')"
