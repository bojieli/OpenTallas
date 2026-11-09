set -e
cd /home/ubuntu/OpenTallas
ssh -n -o ControlPath=none intel2 'cd /home/ubuntu/OpenTallas; timeout 200 git fetch -q origin refs/heads/claude/kw-fix-39-picker-1108:refs/heads/claude/kw-fix-39-picker-1108 refs/heads/claude/s81-transport-fix-1108:refs/heads/claude/s81-transport-fix-1108 refs/heads/claude/hbm-hard-8-epm-1108:refs/heads/claude/hbm-hard-8-epm-1108; git rev-parse claude/kw-fix-39-picker-1108'
timeout 250 git fetch -q origin main refs/heads/claude/kw-fix-39-picker-1108:refs/remotes/origin/claude/kw-fix-39-picker-1108 refs/heads/claude/s81-transport-fix-1108:refs/remotes/origin/claude/s81-transport-fix-1108 refs/heads/claude/hbm-hard-8-epm-1108:refs/remotes/origin/claude/hbm-hard-8-epm-1108
git rev-parse --short=11 origin/main
for s in c78f5970ba5 930bc9c0c25 cb2ae0b99500; do echo "$s ahead=$(git rev-list --count origin/main..$s)"; git diff --stat=100 origin/main...$s | tail -1; done
cd /srv/opentallas-scratch3/claude/rm55
chmod -R u+w /dev/shm/rm55/tmp; rm -rf /dev/shm/rm55/tmp/*
O=$(./build_train.sh refs/rm55/N O "c78f5970ba5|claude/kw-fix-39-picker-1108@c78f5970ba5"); echo O=$O
git -C /home/ubuntu/OpenTallas ls-tree -r --name-only refs/rm55/N | grep -E '(^|/)test_[^/]*\.py$' > base_tests.txt
./mktree.sh $O o
nohup setsid ./runtests.sh o 80 > out_o.txt 2>&1 < /dev/null &
echo launched
