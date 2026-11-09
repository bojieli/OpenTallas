# usage: bash -s <new-tip> <old-tip> <sha...>
set -u
N=$1; OLD=$2; shift 2
cd /home/ubuntu/OpenTallas
exec 9>/home/ubuntu/coord/merge.lock; flock -w 120 9 || { echo LOCKBUSY; exit 9; }
git cat-file -t $N >/dev/null || { echo NOOBJ; exit 1; }
[ "$(git rev-parse HEAD)" = "$(git rev-parse $OLD)" ] || { echo HEADMOVED $(git rev-parse --short=11 HEAD); exit 2; }
timeout 200 git fetch -q origin main || { echo FETCHFAIL; exit 3; }
[ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] || { echo ORIGINMOVED; exit 4; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo DIRTY; git status --porcelain --untracked-files=no | head; exit 5; }
git merge -q --ff-only $N || { echo FFFAIL; exit 6; }
timeout 250 git push -q origin main || { echo PUSHFAIL; exit 7; }
git fetch -q origin main
echo HEAD=$(git rev-parse --short=11 HEAD) ORIGIN=$(git rev-parse --short=11 origin/main) dirty=$(git status --porcelain --untracked-files=no | wc -l)
for s in "$@"; do git merge-base --is-ancestor $s HEAD && echo anc $s || echo MISSING $s; done
