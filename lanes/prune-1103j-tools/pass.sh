#!/bin/bash
# PRUNE-1103J repeat pass: pass.sh <tag> host... ; class 5 only (superseded attempts >6 h). Rebuilds refs, live cmdlines, walks, manifest; del.py rechecks each row.
tag=$1; shift; T=~/coord/lanes/prune-1103j-tools; cd /tmp
python3 $T/refs.py
python3 /tmp/p1103j_cmd.py > /tmp/p1103j_live_local.txt
for h in intel1 intel2 epyc2; do scp -q -o ControlPath=none /tmp/p1103j_cmd.py $h:/tmp/p1103j_cmd.py; ssh -o ControlPath=none $h 'python3 /tmp/p1103j_cmd.py' > /tmp/p1103j_live_$h.txt; done
for h in "$@"; do ssh -o ControlPath=none $h 'rm -f /tmp/p1103j_walk.tsv*; nice -n 15 ionice -c3 python3 /tmp/p1103j_walk.py /srv/opentallas-scratch2 /tmp/p1103j_walk.tsv 7'
 scp -q -o ControlPath=none $h:/tmp/p1103j_walk.tsv /tmp/p1103j_walk_$h.tsv; scp -q -o ControlPath=none $h:/tmp/p1103j_walk.tsv.links /tmp/p1103j_walk_$h.tsv.links
 python3 $T/cands.py $h /tmp/p1103j_walk_$h.tsv /tmp/p1103j_cand_$h.tsv | grep -E 'ELIGIBLE|KEPT GB' | cut -c1-300
 M=~/coord/lanes/PRUNE-1103J-$h-$tag.tsv
 { printf 'path\tsize_GB\tlast_mtime\treason\tclass\n'; awk -F'\t' '$5=="attempt"{printf "%s:%s\t%s\t%s\t%s; idle>6h, unsigned, no .keep, unreferenced, no live process\t%s\n",$1,$2,$3,$4,$6,$5}' /tmp/p1103j_cand_$h.tsv; } > $M
 scp -q -o ControlPath=none $M $h:/tmp/p1103j_man.tsv
 ssh -o ControlPath=none $h 'df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1; timeout 900 nice python3 /tmp/p1103j_del.py /tmp/p1103j_man.tsv del > /tmp/p1103j_del.log 2>&1; tail -1 /tmp/p1103j_del.log | cut -c1-300; grep -c PARTIAL /tmp/p1103j_del.log; df -BG --output=avail,pcent /srv/opentallas-scratch2 | tail -1'
 scp -q -o ControlPath=none $h:/tmp/p1103j_del.log /tmp/p1103j_del_$h.log
 python3 - "$M" /tmp/p1103j_del_$h.log <<'PY'
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
done; date
