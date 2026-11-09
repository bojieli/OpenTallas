cd /srv/opentallas-scratch3/claude/rm55
nproc
for x in "dac437dbaad b" "refs/rm55/L l" "refs/rm55/M m" "refs/rm55/N n"; do set -- $x; ./mktree.sh $1 $2 & done; wait
for t in b l m n; do ./runtests.sh $t 40 > out_$t.txt 2>&1 & done; wait
cat out_*.txt
