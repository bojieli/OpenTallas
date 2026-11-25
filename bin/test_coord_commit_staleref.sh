#!/bin/bash
# bin/test_coord_commit_staleref.sh -- HUB-PUSH-ROTATE 11-25. Fails if coord-commit.sh reports FAILED, or leaves origin/coord/state stale,
# after a push that succeeded while remote.origin.fetch maps only main (the 11-25 02:52-03:32 hub stall).
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/coord-commit.sh
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q --bare "$T/o.git"
git clone -q "$T/o.git" "$T/c" 2>/dev/null; cd "$T/c" || exit 2
git checkout -q -b coord/state; echo a > f; git add f; git commit -q -m init; git push -q origin coord/state
git config --unset-all remote.origin.fetch; git config remote.origin.fetch "+refs/heads/main:refs/remotes/origin/main"   # the broken hub config
git update-ref -d refs/remotes/origin/coord/state 2>/dev/null
echo b >> f
out=$(COORD_DIR="$T/c" COORD_BRANCH=coord/state COORD_COMMIT_TLOG="$T/tlog" timeout 60 bash "$S" "test post" f 2>&1); rc=$?
rt=$(git --git-dir="$T/o.git" rev-parse coord/state); tr=$(git rev-parse refs/remotes/origin/coord/state 2>/dev/null || echo none)
if [ $rc -ne 0 ] || ! grep -q '^PUSHED ' <<<"$out"; then echo "FAIL: rc=$rc out=$out"; exit 1; fi
if [ "$rt" != "$(git rev-parse HEAD)" ]; then echo "FAIL: remote tip $rt != HEAD"; exit 1; fi
if [ "$tr" != "$rt" ]; then echo "FAIL: push succeeded but origin/coord/state is stale ($tr vs $rt)"; exit 1; fi
echo "PASS coord-commit stale-tracking-ref check"
