#!/bin/bash
# PRUNE-1104M pass: pass.sh <tag> list|del host... list = walk+refs+manifest+del.py list; del = del.py del on the existing manifest (rechecks each row).
tag=$1; mode=$2; shift 2; T=~/coord/lanes/prune-1104m-tools; cd /tmp
cat ~/coord/PROTECTED-DBS.txt ~/coord/lanes/PROTECTED-DBS.txt > /tmp/p1104m_prot.txt
if [ $mode = list ]; then
 python3 $T/refs.py; for h in "$@"; do python3 $T/term.py $h; done; cp $T/cmd.py /tmp/p1104m_cmd.py; python3 /tmp/p1104m_cmd.py > /tmp/p1104m_live_local.txt
 for h in intel1 intel2 epyc2; do scp -q -o ControlPath=none $T/cmd.py $h:/tmp/p1104m_cmd.py; ssh -n -o ControlPath=none $h 'python3 /tmp/p1104m_cmd.py' > /tmp/p1104m_live_$h.txt; done
fi
for h in "$@"; do
 scp -q -o ControlPath=none $T/walk.py $h:/tmp/p1104m_walk.py; scp -q -o ControlPath=none $T/del.py $h:/tmp/p1104m_del.py; scp -q -o ControlPath=none /tmp/p1104m_prot.txt $h:/tmp/p1104m_prot.txt
 M=~/coord/lanes/PRUNE-1104M-$h-$tag.tsv
 if [ $mode = list ]; then
  ssh -n -o ControlPath=none $h 'rm -f /tmp/p1104m_walk.tsv*; nice -n 15 ionice -c3 python3 /tmp/p1104m_walk.py /srv/opentallas-scratch2 /tmp/p1104m_walk.tsv 7'
  scp -q -o ControlPath=none $h:/tmp/p1104m_walk.tsv /tmp/p1104m_walk_$h.tsv; scp -q -o ControlPath=none $h:/tmp/p1104m_walk.tsv.links /tmp/p1104m_walk_$h.tsv.links; scp -q -o ControlPath=none $h:/tmp/p1104m_walk.tsv.recent /tmp/p1104m_recent_$h.tsv
  python3 $T/cands.py $h /tmp/p1104m_walk_$h.tsv /tmp/p1104m_cand_$h.tsv > /tmp/p1104m_rep_$h.txt
  grep -E 'ELIGIBLE|KEPT GB' /tmp/p1104m_rep_$h.txt | cut -c1-400
  TAG=$tag python3 $T/finalize.py $h | cut -c1-500
  scp -q -o ControlPath=none $M $h:/tmp/p1104m_man.tsv
  ssh -n -o ControlPath=none $h 'P1104M_RULE='$RULE' timeout 1500 nice python3 /tmp/p1104m_del.py /tmp/p1104m_man.tsv list > /tmp/p1104m_list.log 2>&1; tail -1 /tmp/p1104m_list.log | cut -c1-400'
 else
  scp -q -o ControlPath=none $M $h:/tmp/p1104m_man.tsv
  ssh -n -o ControlPath=none $h "df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1; P1104M_RULE='$RULE' timeout 2400 nice python3 /tmp/p1104m_del.py /tmp/p1104m_man.tsv del > /tmp/p1104m_del.log 2>&1; tail -1 /tmp/p1104m_del.log | cut -c1-400; grep -c PARTIAL /tmp/p1104m_del.log; df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1"
  scp -q -o ControlPath=none $h:/tmp/p1104m_del.log /tmp/p1104m_del_$h.log
  python3 - "$M" /tmp/p1104m_del_$h.log <<'PY'
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
