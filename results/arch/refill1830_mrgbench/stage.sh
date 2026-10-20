#!/bin/bash
# stage.sh BRANCH : merge-tree(main, branch) snapshot of bench-read paths -> $R/<branch>/src
set -eu
export GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
R=/srv/opentallas-scratch/claude/refill-1830/MRGBENCH; b=$1; shift
git fetch -q origin +main:refs/refill1830/main +claude/$b:refs/refill1830/$b
M=$(git rev-parse refs/refill1830/main); B=$(git rev-parse refs/refill1830/$b)
T=$(git merge-tree --write-tree refs/refill1830/main refs/refill1830/$b | head -1) || true
C=$(git merge-tree --write-tree --name-only refs/refill1830/main refs/refill1830/$b | sed -n '2,/^$/p' | grep -v '^$' || true)
D=$R/$b; rm -rf $D/src; mkdir -p $D/src
P=""; for p in "$@"; do git cat-file -e $T:$p 2>/dev/null && P="$P $p"; done
git archive $T $P | tar -x -C $D/src
printf 'main %s\nbranch %s\ntree %s\nconflicts %s\npaths%s\n' $M $B $T "$(echo $C | tr '\n' ' ')" "$P" > $D/stage.txt
cat $D/stage.txt; du -sh $D/src | cut -f1
