#!/bin/bash
# otrun-hub-backup.sh -- INFRA2 2026-10-24: nightly copy of the NON-SECRET state of the ot-run hub (epyc1 = tender-ray)
# to the other disk (/srv/opentallas-scratch2/hub-backup; md0 root is a degraded 1-disk RAID1 since 10-24).
# The archive copy (155.103.253.53:/archive/otrun-hub/) is pulled from rtx-pro (~/bin/otrun-hub-archive.sh),
# because epyc1 has no key for the archive.  Private keys are NEVER copied (only their file names are recorded).
# Recovery recipe: coord/state lanes/OTRUN-HUB-RECOVERY.md.
set -u
DST=${OTRUN_HUB_BACKUP_DST:-/srv/opentallas-scratch2/hub-backup}
LOG=$HOME/.local/state/otrun-hub-backup.log
exec 9>/tmp/otrun-hub-backup.lock; flock -n 9 || { echo "$(date -Is) already running" >>"$LOG"; exit 0; }
mkdir -p "$DST/files" "$DST/meta"
rc=0
R() { rsync -aR --delete-after "$@" "$DST/files/" || rc=$?; }
# launcher + per-host admission tools + their config
R $HOME/.local/bin/ot-run $HOME/.local/bin/ot-run.bak* $HOME/.local/bin/ot-sizes-sync
R /usr/local/bin/ot-heavy /usr/local/bin/ot-heavy-reconcile /usr/local/bin/ot-protect-die /usr/local/bin/ot-vl-jcap
R /etc/ot-heavy.conf /etc/ot-oomadj-legacy-cutoff /etc/systemd/system/ot-die-protection.service
# launcher state (small): signals log, spill pending records, held hosts, daemon job index, fleet size tables
R $HOME/.local/state/ot-run $HOME/.config/ot-run $HOME/.local/state/closure_loop $HOME/.local/state/die-ci
rm -rf "$DST/files/var/tmp/ot-heavy"   # small; recopied each run so per-job files never accumulate
V=(); for f in sizes.json sizes.fleet.json die-protection.json admit.log exit.log reconcile.log; do
  [ -e /var/tmp/ot-heavy/$f ] && V+=(/var/tmp/ot-heavy/$f); done   # tables + logs, not the per-job pids/res/use/meta files
[ ${#V[@]} -gt 0 ] && R "${V[@]}"
# ssh: config + public material only (NO private keys)
R $HOME/.ssh/config $HOME/.ssh/known_hosts $HOME/.ssh/authorized_keys $HOME/.ssh/id_ed25519.pub
# user units + this script; EDA tools that ot-heavy puts on PATH
R $HOME/.config/systemd/user $HOME/bin/otrun-hub-backup.sh $HOME/bin/hub-git-sync.sh $HOME/.local/opentallas-tools
# metadata
M=$DST/meta
crontab -l >"$M/crontab.txt" 2>&1
systemctl --user list-unit-files --no-pager >"$M/user-unit-files.txt" 2>&1
systemctl --user list-timers --all --no-pager >"$M/user-timers.txt" 2>&1
docker images --digests --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Digest}} {{.Size}}' >"$M/docker-images.txt" 2>&1
ls -la $HOME/.ssh | awk '{print $1, $NF}' >"$M/ssh-key-files.txt"   # names only; id_ed25519 (private) is NOT copied
{ hostname; date -Is; cat /proc/mdstat; df -h / /srv/opentallas-scratch2; nproc; free -g; } >"$M/host.txt" 2>&1
git -C $HOME/coord log -1 --format='%H %cI' >"$M/coord-head.txt" 2>&1
echo "$(date -Is) rc=$rc" >"$M/last-run.txt"
echo "$(date -Is) backup rc=$rc to $DST ($(du -sh "$DST" | cut -f1))" >>"$LOG"
exit $rc
