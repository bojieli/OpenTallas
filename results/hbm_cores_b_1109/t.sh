cd /home/ubuntu/OpenTallas
timeout 250 git fetch -q origin main refs/heads/claude/kw-fix-40-resume-1108:refs/remotes/origin/claude/kw-fix-40-resume-1108 refs/heads/claude/s81-svc-8-eng-1108:refs/remotes/origin/claude/s81-svc-8-eng-1108 refs/heads/claude/die-head-88-tapbal-esc-1108:refs/remotes/origin/claude/die-head-88-tapbal-esc-1108
git rev-parse --short=11 origin/main
for s in 215b178d640 f0ecae8143 422126acd12; do echo "== $s ahead=$(git rev-list --count origin/main..$s) conflict=$(git merge-tree --write-tree origin/main $s >/dev/null 2>&1; echo $?)"; git diff --stat=90 origin/main...$s | tail -5 | cut -c1-100; done
for t in q r s; do git worktree remove --force /dev/shm/rm55/$t; done
cd /srv/opentallas-scratch3/claude/rm55
R=c72bf058dc7e3c17a5b269d978548c084e373ca3
T=$(./build_train.sh $R T "c50c0711850|claude/s81-transport-fix-1108@c50c0711850" "215b178d640|claude/kw-fix-40-resume-1108@215b178d640") || exit 1
U=$(./build_train.sh $T U "f0ecae8143|claude/s81-svc-8-eng-1108@f0ecae8143" "422126acd12|claude/die-head-88-tapbal-esc-1108@422126acd12" "259223d3910|claude/qc-transport-fix-1108@259223d3910") || exit 1
echo T=$T U=$U
git -C /home/ubuntu/OpenTallas ls-tree -r --name-only $R | grep -E '(^|/)test_[^/]*\.py$' > base_tests.txt
./mktree.sh $T t; ./mktree.sh $U u
for t in t u; do ./runtests.sh $t 60 > out_$t.txt 2>&1 & done; wait
echo ALLDONE
