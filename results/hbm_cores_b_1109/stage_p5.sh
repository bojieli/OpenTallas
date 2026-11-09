#!/bin/bash
# DIE-KV-97: stage src_p5 on this host = local read-only wave src kw37/src_e2rd_lg + the 14-file delta (queue_src claude/die-kv-97-p4src-1109@faeb1ac9)
set -eu
R=$(readlink -f /srv/opentallas-scratch2/claude/kw37/src_e2rd_lg); N=/srv/opentallas-scratch2/claude/dkv97/src_p5; T=/srv/opentallas-scratch2/claude/dkv97/src_p5_delta.tgz
test ! -L "$R"; test -d "$R"; test ! -e "$N"
md5sum -c <(echo "88ea14a320075263ebf19913ae04bd1b  $T")
cp -al "$R" "$N"; find "$N" -type d -exec chmod u+w {} +; cd "$N"
tar tzf "$T" | grep -v '/$' | while read -r f; do rm -f -- "$f"; done
tar xzf "$T"
while read -r m f; do echo "$m  $f"; done < /srv/opentallas-scratch2/claude/dkv97/src_p5_delta.tsv | md5sum -c --quiet
find . -type d -exec chmod a-w {} +; tar tzf "$T" | grep -v '/$' | while read -r f; do chmod a-w -- "$f"; done
echo STAGED_SRC_P5 $(hostname)
