set -e
mkdir -p /srv/opentallas-scratch3/claude/rm55 /dev/shm/rm55
cd /srv/opentallas-scratch3/claude/rm55
cat > build_train.sh <<'S'
#!/bin/bash
# usage: build_train.sh <base-sha> <outname> <sha|label> ...  -> prints new tip; no pushes
set -euo pipefail
R=/home/ubuntu/OpenTallas
base=$1; name=$2; shift 2
cur=$base
AE=$(git -C $R log -1 --format=%ae dac437dbaad); CE=$(git -C $R log -1 --format=%ce dac437dbaad)
for item in "$@"; do
  s=${item%%|*}; l=${item##*|}
  if git -C $R merge-base --is-ancestor $s $cur; then echo "SKIP already in: $l" >&2; continue; fi
  tree=$(git -C $R merge-tree --write-tree $cur $s) || { echo "CONFLICT $l" >&2; echo "$tree" | head -20 >&2; exit 2; }
  d=$(git -C $R diff --diff-filter=D --name-only $cur $tree | wc -l)
  [ "$d" = 0 ] || { echo "DELETIONS $d in $l" >&2; git -C $R diff --diff-filter=D --name-only $cur $tree | head >&2; exit 3; }
  msg="Merge ROOT-MERGE-55: $l"$'\n\n'"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  cur=$(GIT_AUTHOR_NAME="Bojie Li" GIT_COMMITTER_NAME="Bojie Li" GIT_AUTHOR_EMAIL="$AE" GIT_COMMITTER_EMAIL="$CE" git -C $R commit-tree -p $cur -p $s -m "$msg" $tree)
  echo "$cur $l" >&2
done
git -C $R update-ref refs/rm55/$name $cur
echo $cur
S
cat > mktree.sh <<'S'
#!/bin/bash
# usage: mktree.sh <sha> <name> : sparse (<1 MiB files) worktree under /dev/shm/rm55/<name>
set -euo pipefail
R=/home/ubuntu/OpenTallas; sha=$1; T=/dev/shm/rm55/$2
git -C $R worktree add -q --no-checkout --detach $T $sha
git -C $T read-tree $sha
git -C $T ls-tree -r -l -z $sha | python3 -I -c '
import sys
for rec in sys.stdin.buffer.read().split(b"\0"):
    if not rec: continue
    meta,path=rec.split(b"\t",1); f=meta.split()
    if f[1]==b"blob" and f[3]!=b"-" and int(f[3])<1048576:
        sys.stdout.buffer.write(path+b"\0")
' | git -C $T checkout-index -z --stdin
echo ok $2 $(du -sh $T | cut -f1)
S
cat > runtests.sh <<'S'
#!/bin/bash
# usage: runtests.sh <treename> <P>  ; logs to rm55/<tree>/ ; selection = rm54 l_t set + new test files
T=/dev/shm/rm55/$1; L=/srv/opentallas-scratch3/claude/rm55/$1; P=${2:-48}
mkdir -p $L /dev/shm/rm55/tmp/$1
cd $T
git ls-files -z | python3 -I -c '
import sys,os
l=set(os.listdir("/srv/opentallas-scratch3/claude/rm54/l_t"))
base=set(open("/srv/opentallas-scratch3/claude/rm55/base_tests.txt").read().split())
for p in sys.stdin.read().split("\0"):
    n=os.path.basename(p)
    if not(n.startswith("test_") and n.endswith(".py")): continue
    if p.replace("/","_")+".log" in l or p not in base: print(p)
' > $L/list.txt
export T L
one(){ f=$1; n=${f//\//_}; cd $T; timeout 900 python3 -m pytest -q -p no:cacheprovider --basetemp=/dev/shm/rm55/tmp/${T##*/}/$n "$f" > $L/$n.log 2>&1; echo "$? $f" >> $L/rc.txt; rm -rf /dev/shm/rm55/tmp/${T##*/}/$n; }
export -f one
: > $L/rc.txt
xargs -a $L/list.txt -P $P -I{} bash -c 'one {}'
grep -h -E "^(FAILED|ERROR) " $L/*.log | sed "s/ - .*//" | sort -u > $L/fails.txt
awk '$1!=0 {print $2}' $L/rc.txt | sort > $L/nz.txt
echo done $(wc -l < $L/list.txt) files fails $(wc -l < $L/fails.txt)
S
chmod +x *.sh
git -C /home/ubuntu/OpenTallas ls-tree -r --name-only dac437dbaad | grep -E '(^|/)test_[^/]*\.py$' > base_tests.txt
wc -l base_tests.txt
git -C /home/ubuntu/OpenTallas config user.name; git -C /home/ubuntu/OpenTallas log -1 --format='%an <%ae> | %cn <%ce>' dac437dbaad
B=dac437dbaad
L=$(./build_train.sh $B L "84ac53507bb|claude/kw-fix-38-picker-1108@84ac53507bb" "173a0b28163|codex/qc-hc1-forward-reserve-1113@173a0b2816" "41a1123579d|codex/qc-hc3-flat-state-1113@41a1123579d")
M=$(./build_train.sh $L M "9c2a8b7c9f8a|claude/s81-types-10-rck-1108@9c2a8b7c9f8a" "6c1693a7347|claude/transport-2-1108@6c1693a734")
N=$(./build_train.sh $M N "97e557d9a03|claude/die-s81-81-pkrst-1108@97e557d9a03" "fdfd08eb4d5|claude/transport-3-1108@fdfd08eb4d5")
echo L=$L M=$M N=$N
