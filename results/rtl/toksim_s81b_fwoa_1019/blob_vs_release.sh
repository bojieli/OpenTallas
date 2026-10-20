#!/bin/bash
# every file a bench build read (sources.sha256) -> git blob vs release GEN mu4c 19bf4121e and origin/main
D=/srv/opentallas-scratch/claude/toksim-s81b-fwoa; cd $D/root
for S in "$@"; do echo "## $S"; awk '{print $2}' $S | while read f; do b=$(git hash-object $f)
  r=$(awk -v f="$f" '$2==f{print $1}' $D/release_blobs.txt); m=$(awk -v f="$f" '$2==f{print $1}' $D/main_blobs.txt)
  s=DIFF; [ "$b" = "$r" ] && s=RELEASE; [ -z "$r" ] && s=NOT_IN_RELEASE; echo "$s $b $f release=${r:-none} main=${m:-n/a}"; done; done
