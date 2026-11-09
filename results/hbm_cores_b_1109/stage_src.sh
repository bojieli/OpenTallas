#!/bin/bash
# DIE-KV-96: stage src_p4 on this host from its local read-only wave src + the 14-file delta (hard links, delta files as new inodes)
set -eu
R=$(readlink -f /srv/opentallas-scratch2/claude/kw37/src_e2rd_lg)
N=/srv/opentallas-scratch2/claude/dkv95/src_p4
test ! -L "$R"; test -d "$R"
mkdir -p /srv/opentallas-scratch2/claude/dkv95
test ! -e "$N" || { echo "EXISTS $N"; exit 3; }
cp -al "$R" "$N"
find "$N" -type d -exec chmod u+w {} +
cd "$N"
T=/srv/opentallas-scratch2/claude/dkv95/src_p4_delta.tgz
tar tzf "$T" | grep -v '/$' | while read -r f; do rm -f -- "$f"; done
tar xzf "$T"
tar tzf "$T" | grep -v '/$' | wc -l
find . -type d -exec chmod a-w {} +
tar tzf "$T" | grep -v '/$' | while read -r f; do chmod a-w -- "$f"; done
echo STAGED_SRC $(hostname)
