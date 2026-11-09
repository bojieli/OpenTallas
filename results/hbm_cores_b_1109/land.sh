set -u
cd /home/ubuntu/OpenTallas
N=fd5986250793d32318eae0a61e03f04f9a41c817
exec 9>/home/ubuntu/coord/merge.lock; flock -w 120 9 || { echo LOCKBUSY; exit 9; }
git cat-file -t $N >/dev/null || { echo NOOBJ; exit 1; }
[ "$(git rev-parse HEAD)" = "$(git rev-parse dac437dbaad)" ] || { echo HEADMOVED $(git rev-parse --short=11 HEAD); exit 2; }
timeout 200 git fetch -q origin main || { echo FETCHFAIL; exit 3; }
[ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] || { echo ORIGINMOVED; exit 4; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo DIRTY; git status --porcelain --untracked-files=no | head; exit 5; }
git merge -q --ff-only $N || { echo FFFAIL; exit 6; }
timeout 250 git push -q origin main || { echo PUSHFAIL; exit 7; }
git fetch -q origin main
echo HEAD=$(git rev-parse --short=11 HEAD) ORIGIN=$(git rev-parse --short=11 origin/main) dirty=$(git status --porcelain --untracked-files=no | wc -l)
for s in 84ac53507bb 173a0b28163 41a1123579d 9c2a8b7c9f8a 6c1693a7347 97e557d9a03 fdfd08eb4d5; do git merge-base --is-ancestor $s HEAD && echo anc $s || echo MISSING $s; done
git tag -l 'flow-20261108-e[kstir]*' 'flow-20261108-f[s]*' --points-at dac437dbaad; git cat-file -t flow-20261108-ek-head; git for-each-ref --format='%(refname:short) %(taggername)|%(contents:subject)' refs/tags/flow-20261108-fs-hbm | cut -c1-200
