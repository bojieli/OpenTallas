#!/bin/bash
# usage: p1104m_wt.sh name  -> read-only gate data for one epyc2 root worktree
# usage: wtgate.sh name [root/]  read-only gate data
T=~/coord/lanes/prune-1104m-tools; n=$1; RT=${2:-/home/ubuntu/scratch-root/claude/}
scp -q -o ControlPath=none $T/wtcheck.py $T/wtrefs.py epyc2:/tmp/ 
ssh -n -o ControlPath=none epyc2 "cd $RT; nice -n 15 ionice -c3 python3 /tmp/wtrefs.py /tmp/p1104m_wtrefs.tsv $n; cut -f1,2 /tmp/p1104m_wtrefs.tsv | head -40 | cut -c1-200; WT_ROOT=$RT nice python3 /tmp/wtcheck.py $n > /tmp/p1104m_wtc.json; find /home/ubuntu/scratch-root/claude /srv/opentallas-scratch2/claude -xdev -maxdepth 4 -type l -lname '*$n*' 2>/dev/null | head; git -C $RT$n log -1 --format='HEAD %h %cd %s' --date=iso | cut -c1-120"
scp -q -o ControlPath=none epyc2:/tmp/p1104m_wtc.json /tmp/p1104m_wtc.json
python3 - <<'P'
import json
for l in open('/tmp/p1104m_wtc.json'):
    o=json.loads(l); h=o.get('holders',[]); o['holders']=[':'.join(x.split(':')[:2]) for x in h]; o['recent']=o.get('recent',[])[:4]; o['modified']=o.get('modified',[])[:8]; o['untracked']=o.get('untracked',[])[:8]; o['ignored']=o.get('ignored',[])[:8]; o['untracked_views']=o.get('untracked_views',[])[:6]
    print(json.dumps(o,indent=0)[:3000])
P
date
