#!/bin/bash
# PRUNE-1104M read-only citation scan, grep -F form of attcite.py (the python form ran >1 h CPU bound and died with no output at 05:3x).
# usage on host: attcite.sh manifest.tsv cited.txt  ; cited = attempts a text file outside the attempt itself names by path. attempt_2 also hits attempt_2x: over-cites only.
# Not citers: hub-coord (coord/state checkout: refs.py and term.py classify those files from ~/coord) and prune lanes' own manifests and lists.
man=$1; out=$2; W=$(mktemp -d /tmp/p1104m_ac.XXXX); R=/srv/opentallas-scratch2/claude
tail -n +2 "$man" | cut -f1 | cut -d: -f2- | sed -E 's#.*/([^/]+/items/[^/]+/attempt_[0-9]+)$#\1#' | sort -u > $W/pats
find $R -xdev \( -name .git -o -name objects -o -name results -o -name __pycache__ -o -path $R/hub-coord -o -name 'prune-*' -o -name 'PRUNE-*' \) -prune -o -type f -size -2048k \( -name '*.f' -o -name '*.json' -o -name '*.sh' -o -name '*.tcl' -o -name '*.mk' -o -name '*.env' -o -name '*.yaml' -o -name '*.yml' -o -name '*.txt' -o -name '*.py' -o -name '*.sdc' -o -name '*.cfg' -o -name '*.tsv' -o -name '*.manifest' -o -name Makefile \) -print0 | xargs -0 -r -n 500 -P 6 sh -c 'nice -n 15 ionice -c3 grep -HoF -f "$0" "$@" 2>/dev/null >> "$0.hits.$$"; exit 0' $W/pats
cat $W/pats.hits.* > $W/hits 2>/dev/null  # one output file per grep: a shared stdout interleaved lines and could lose a citation
python3 - "$man" "$W/hits" "$out" <<'P'
import sys,re
man,hits,out=sys.argv[1:4]
rows=[l.split('\t')[0].split(':',1)[1] for l in list(open(man))[1:]]
key={re.search(r'[^/]+/items/[^/]+/attempt_\d+$',p).group():p for p in rows if '/items/' in p}
cited={};n=0
for l in open(hits,errors='replace'):
    fp,_,k=l.rstrip('\n').rpartition(':'); n+=1
    t=key.get(k)
    if not t or fp.startswith(t+'/'): continue
    cited.setdefault(t,fp)
open(out+'.tmp','w').write(''.join(k+'\n' for k in cited)); import os; os.rename(out+'.tmp',out)
open(out+'.why','w').write(''.join(f'{k}\t{v}\n' for k,v in cited.items()))
print('hits',n,'rows',len(rows),'cited',len(cited))
P
cp $W/hits $out.hits; rm -rf $W; date
