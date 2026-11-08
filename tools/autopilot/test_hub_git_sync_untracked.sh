#!/bin/bash
# KW-FIX-35 11-08: hub_git_sync.sh coord (1) self-heals an identical untracked file in the way, (2) refuses a differing
# one with an ALERT line in the log.
set -u
S=$(cd "$(dirname "$0")" && pwd)/hub_git_sync.sh
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q --bare "$T/origin.git"
git clone -q "$T/origin.git" "$T/a" 2>/dev/null; cd "$T/a"; git checkout -q -b coord/state
mkdir lanes; echo x > lanes/Q.md; git add lanes; git commit -qm i; git push -q origin coord/state
git clone -q -b coord/state "$T/origin.git" "$T/hub" 2>/dev/null
# other host adds handoff/h.md + h2.md on origin; the hub has the same h.md untracked, plus one local commit
mkdir -p handoff; echo same > handoff/h.md; git add handoff; git commit -qm h; git push -q origin coord/state
cd "$T/hub"; mkdir -p handoff; echo same > handoff/h.md; echo y >> lanes/Q.md; git commit -qam local
fail=0
HUB_SYNC_COORD="$T/hub" bash "$S" coord >/dev/null 2>&1 || { echo "FAIL identical case rc"; fail=1; }
[ "$(git rev-parse HEAD)" = "$(git -C "$T/origin.git" rev-parse coord/state)" ] || { echo "FAIL not pushed"; fail=1; }
[ -f autopilot/.hub-sync-untracked/handoff/h.md ] || { echo "FAIL not kept aside"; fail=1; }
# differing untracked copy: refuse loudly
cd "$T/a"; git pull -q origin coord/state; echo theirs > handoff/d.md; git add handoff/d.md; git commit -qm d; git push -q origin coord/state
cd "$T/hub"; echo mine > handoff/d.md; echo z >> lanes/Q.md; git commit -qam local2
HUB_SYNC_COORD="$T/hub" bash "$S" coord >/dev/null 2>&1 && { echo "FAIL differing case merged"; fail=1; }
grep -q "ALERT HUB-SYNC-FAILED .*differ from origin: handoff/d.md" autopilot/log.txt || { echo "FAIL no ALERT"; cat autopilot/log.txt; fail=1; }
[ "$(cat handoff/d.md)" = mine ] || { echo "FAIL local copy touched"; fail=1; }
[ $fail = 0 ] && echo "test_hub_git_sync_untracked OK"; exit $fail
