#!/bin/bash
# otrun-hub-archive.sh -- INFRA2 2026-10-24: pull epyc1's ot-run hub backup (made 02:15 by epyc1:~/bin/otrun-hub-backup.sh
# into /srv/opentallas-scratch2/hub-backup; non-secret, no private keys) and push it to the archive
# 155.103.253.53:/archive/otrun-hub/ (epyc1 has no archive key, rtx-pro has ~/.ssh/agidock_ot).
set -u
MIR=/home/ubuntu/.cache/otrun-hub-mirror; LOG=/home/ubuntu/.cache/otrun-hub-archive.log
exec 9>/home/ubuntu/.cache/otrun-hub-archive.lock; flock -n 9 || exit 0
mkdir -p "$MIR"
rsync -a --delete-after -e "ssh -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=20" epyc1:/srv/opentallas-scratch2/hub-backup/ "$MIR/"; r1=$?
SSH="ssh -i /home/ubuntu/.ssh/agidock_ot -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=20"
$SSH ubuntu@155.103.253.53 'mkdir -p /archive/otrun-hub && chmod 700 /archive/otrun-hub'; r2=$?
rsync -a --delete-after -e "$SSH" "$MIR/" ubuntu@155.103.253.53:/archive/otrun-hub/; r3=$?
echo "$(date -Is) pull=$r1 mkdir=$r2 push=$r3 last-run=$(cat $MIR/meta/last-run.txt 2>/dev/null)" >>"$LOG"
[ $r1 = 0 ] && [ $r3 = 0 ]
