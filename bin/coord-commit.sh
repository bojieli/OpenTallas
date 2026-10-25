#!/bin/bash
# usage: coord-commit.sh "message" file1 [file2 ...]   (paths relative to ~/coord) -- serialised commit+push of coord/state
set -e
cd /home/ubuntu/coord
msg="$1"; shift
exec 9>/home/ubuntu/coord/.coord.lock
flock 9
git add -- "$@"
git commit -q -m "$msg" -- "$@" || true
# merge (not rebase): other agents may hold uncommitted edits in this shared tree, which rebase refuses and stash must never touch
for i in 1 2 3 4 5; do git fetch -q origin coord/state && git merge -q --no-edit origin/coord/state && git push -q origin coord/state && exit 0; sleep 3; done
echo "coord push failed" >&2; exit 1
