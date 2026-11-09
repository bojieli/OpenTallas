cd /home/ubuntu/OpenTallas
timeout 250 git fetch -q origin main refs/heads/claude/die-hbm-94-kitflow-1108:refs/remotes/origin/claude/die-hbm-94-kitflow-1108 refs/heads/claude/die-hbm-94-pdn-1108:refs/remotes/origin/claude/die-hbm-94-pdn-1108 refs/heads/claude/die-hbm-94-hostcp-1108:refs/remotes/origin/claude/die-hbm-94-hostcp-1108 refs/heads/claude/s81-transport-fix-1108:refs/remotes/origin/claude/s81-transport-fix-1108
git rev-parse --short=11 origin/main
for s in 7428ba78a88b ee38ee88f048 cac6fd2efcd5 c50c0711850; do echo "== $s ahead=$(git rev-list --count origin/main..$s) conflict=$(git merge-tree --write-tree origin/main $s >/dev/null 2>&1; echo $?)"; git diff --stat=90 origin/main...$s | tail -8 | cut -c1-100; done
git -C /home/ubuntu/OpenTallas worktree remove --force /dev/shm/rm55/p
cd /srv/opentallas-scratch3/claude/rm55
Q=43f3749c8afbdbc791c93769dddd09b0fa7cc967
R=$(./build_train.sh $Q R "7428ba78a88b|claude/die-hbm-94-kitflow-1108@7428ba78a88b" "ee38ee88f048|claude/die-hbm-94-pdn-1108@ee38ee88f048" "cac6fd2efcd5|claude/die-hbm-94-hostcp-1108@cac6fd2efcd5") || exit 1
S=$(./build_train.sh $R S "c50c0711850|claude/s81-transport-fix-1108@c50c0711850" "259223d3910|claude/qc-transport-fix-1108@259223d3910") || exit 1
echo R=$R S=$S
git -C /home/ubuntu/OpenTallas ls-tree -r --name-only $Q | grep -E '(^|/)test_[^/]*\.py$' > base_tests.txt
./mktree.sh $R r; ./mktree.sh $S s
(for t in r s; do ./runtests.sh $t 60 > out_$t.txt 2>&1 & done; wait) &
sleep 1; echo launched
