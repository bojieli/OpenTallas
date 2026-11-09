cd /home/ubuntu/OpenTallas
for t in b l m n; do git worktree remove --force /dev/shm/rm55/$t 2>&1 | tail -1; done
find /dev/shm/rm55/tmp -type d -exec chmod u+rwx {} + 2>/dev/null
rm -rf /dev/shm/rm55/tmp/* 2>/dev/null
find /dev/shm/rm55/tmp -type f 2>/dev/null | wc -l
timeout 250 git fetch -q origin main refs/heads/claude/hbm-hard-8-epm-1108:refs/remotes/origin/claude/hbm-hard-8-epm-1108
cd /srv/opentallas-scratch3/claude/rm55
P=$(./build_train.sh ab64dba2a824f871c5f0268b9480ec714fccac21 P "cb2ae0b99500|claude/hbm-hard-8-epm-1108@cb2ae0b99500" "f550f29e619|claude/store-1-srcdedupe-1108@f550f29e619" "204d8062101|claude/store-2-ot-run-robind-1108@204d8062101") || exit 1
echo P=$P
git -C /home/ubuntu/OpenTallas ls-tree -r --name-only ab64dba2a824 | grep -E '(^|/)test_[^/]*\.py$' > base_tests.txt
./mktree.sh $P p
nohup setsid ./runtests.sh p 80 > out_p.txt 2>&1 < /dev/null &
echo launched
