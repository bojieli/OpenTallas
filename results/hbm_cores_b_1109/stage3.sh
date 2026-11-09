#!/bin/bash
# KW-FIX-41: replace one file in a staged hard-link source tree. Usage: stage3.sh <tree-link> <relpath> <new-file>
set -euo pipefail
LN=$1; R=$2; NF=$3
NEW=$(readlink -f "$LN")
[ -d "$NEW" ] || { echo "$(hostname) NO TREE $LN"; exit 0; }
case "$NEW" in */claude/kw41src/*|*/claude/kw41/src_*) ;; *) echo "ERR not my tree $NEW"; exit 3;; esac
F="$NEW/$R"; D=$(dirname "$F")
chmod u+w "$D"
rm -f "$F"; cp "$NF" "$F"; chmod a-w "$F"
chmod a-w "$D"
echo "$(hostname) $NEW md5=$(md5sum "$F" | cut -d' ' -f1) links=$(stat -c %h "$F")"
