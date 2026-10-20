#!/bin/bash
# stage.sh BRANCH KIT... : merge-tree(origin/main, branch) snapshot of bench-read paths -> $R/<branch>/src
set -eu
export GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
R=/srv/opentallas-scratch/claude/refill-0325/MRGBENCH; b=$1; shift
git fetch -q origin +main:refs/refill0325/main +claude/$b:refs/refill0325/$b
M=$(git rev-parse refs/refill0325/main); B=$(git rev-parse refs/refill0325/$b)
O=$(git merge-tree --write-tree --name-only $M $B) || true
T=$(echo "$O" | head -1); C=$(echo "$O" | sed -n '2,/^$/p' | grep -v '^$' | tr '\n' ' ' || true)
P=$(python3 -I $R/collect.py $T "$@")
D=$R/$b; rm -rf $D/src; mkdir -p $D/src
git archive $T $P | tar -x -C $D/src
printf 'main %s\nbranch %s\ntree %s\nkits %s\nconflicts %s\npaths %s\n' $M $B $T "$*" "$C" "$P" > $D/stage.txt
cat $D/stage.txt | cut -c1-400; du -sh $D/src | cut -f1
