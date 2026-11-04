#!/bin/bash
# PRUNE-1103L pass: pass.sh <tag> list|del host... list = walk+refs+manifest+del.py list; del = del.py del on the existing manifest (rechecks each row).
tag=$1; mode=$2; shift 2; T=~/coord/lanes/prune-1103l-tools; cd /tmp
cat ~/coord/PROTECTED-DBS.txt ~/coord/lanes/PROTECTED-DBS.txt > /tmp/p1103l_prot.txt
if [ $mode = list ]; then
 python3 $T/refs.py; cp $T/cmd.py /tmp/p1103l_cmd.py; python3 /tmp/p1103l_cmd.py > /tmp/p1103l_live_local.txt
 for h in intel1 intel2 epyc2; do scp -q -o ControlPath=none $T/cmd.py $h:/tmp/p1103l_cmd.py; ssh -o ControlPath=none $h 'python3 /tmp/p1103l_cmd.py' > /tmp/p1103l_live_$h.txt; done
fi
for h in "$@"; do
 scp -q -o ControlPath=none $T/walk.py $h:/tmp/p1103l_walk.py; scp -q -o ControlPath=none $T/del.py $h:/tmp/p1103l_del.py; scp -q -o ControlPath=none /tmp/p1103l_prot.txt $h:/tmp/p1103l_prot.txt
 M=~/coord/lanes/PRUNE-1103L-$h-$tag.tsv
 if [ $mode = list ]; then
  ssh -o ControlPath=none $h 'rm -f /tmp/p1103l_walk.tsv*; nice -n 15 ionice -c3 python3 /tmp/p1103l_walk.py /srv/opentallas-scratch2 /tmp/p1103l_walk.tsv 7'
  scp -q -o ControlPath=none $h:/tmp/p1103l_walk.tsv /tmp/p1103l_walk_$h.tsv; scp -q -o ControlPath=none $h:/tmp/p1103l_walk.tsv.links /tmp/p1103l_walk_$h.tsv.links
  python3 $T/cands.py $h /tmp/p1103l_walk_$h.tsv /tmp/p1103l_cand_$h.tsv > /tmp/p1103l_rep_$h.txt
  grep -E 'ELIGIBLE|KEPT GB' /tmp/p1103l_rep_$h.txt | cut -c1-400
  TAG=$tag python3 $T/finalize.py $h | cut -c1-500
  scp -q -o ControlPath=none $M $h:/tmp/p1103l_man.tsv
  ssh -o ControlPath=none $h 'timeout 1500 nice python3 /tmp/p1103l_del.py /tmp/p1103l_man.tsv list > /tmp/p1103l_list.log 2>&1; tail -1 /tmp/p1103l_list.log | cut -c1-400'
 else
  scp -q -o ControlPath=none $M $h:/tmp/p1103l_man.tsv
  ssh -o ControlPath=none $h 'df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1; timeout 1500 nice python3 /tmp/p1103l_del.py /tmp/p1103l_man.tsv del > /tmp/p1103l_del.log 2>&1; tail -1 /tmp/p1103l_del.log | cut -c1-400; grep -c PARTIAL /tmp/p1103l_del.log; df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1'
  scp -q -o ControlPath=none $h:/tmp/p1103l_del.log /tmp/p1103l_del_$h.log
  python3 - "$M" /tmp/p1103l_del_$h.log <<'PY'
import sys
m,lg=sys.argv[1:3]; sk={}
for l in open(lg):
    if l.startswith('SKIP'):
        _,w,p=l.split(None,2); sk[p.strip()]=w
r=open(m).read().splitlines(); o=[r[0]+'\tstatus']
for l in r[1:]:
    p=l.split('\t')[0].split(':',1)[1]; o.append(l+'\t'+('SKIPPED:'+sk[p] if p in sk else 'DELETED'))
open(m,'w').write('\n'.join(o)+'\n')
print(m,'deleted',sum(x.endswith('DELETED') for x in o),'GB %.1f'%sum(float(x.split('\t')[1]) for x in o if x.endswith('DELETED')),'skipped',sum('SKIPPED' in x for x in o))
PY
 fi
done; date
