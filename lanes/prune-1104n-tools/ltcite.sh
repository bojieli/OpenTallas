#!/bin/bash
# PRUNE-1104N read-only: scratch text files outside each listed dir that name it (<event>/items/<item>/<sub>). usage on host: ltcite.sh list.txt cited.tsv
L=$1; O=$2; W=$(mktemp -d /tmp/p1104n_lc.XXXX); R=/srv/opentallas-scratch2/claude
sed -E 's#.*/([^/]+/items/[^/]+/[^/]+)$#\1/#' "$L" | sort -u > $W/pats
find $R -xdev \( -name .git -o -name objects -o -name results -o -name __pycache__ -o -path $R/hub-coord -o -name 'prune-*' -o -name 'PRUNE-*' \) -prune -o -type f -size -2048k \( -name '*.f' -o -name '*.json' -o -name '*.sh' -o -name '*.tcl' -o -name '*.mk' -o -name '*.env' -o -name '*.yaml' -o -name '*.yml' -o -name '*.txt' -o -name '*.py' -o -name '*.sdc' -o -name '*.cfg' -o -name '*.tsv' -o -name '*.manifest' -o -name Makefile \) -print0 | xargs -0 -r -n 500 -P 6 sh -c 'nice -n 15 ionice -c3 grep -HoF -f "$0" "$@" 2>/dev/null >> "$0.hits.$$"; exit 0' $W/pats
cat $W/pats.hits.* > $W/hits 2>/dev/null
python3 -I - "$L" "$W/hits" "$O" <<'P'
import sys,re
L,hits,out=sys.argv[1:4]; rows=[l.strip() for l in open(L)]
key={re.search(r'[^/]+/items/[^/]+/[^/]+$',p).group()+'/':p for p in rows}; C={}
for l in open(hits,errors='replace'):
    fp,_,k=l.rstrip('\n').rpartition(':'); t=key.get(k)
    if not t or fp.startswith(t+'/'): continue
    C.setdefault(t,set()).add(fp)
with open(out,'w') as o:
    for t,s in C.items():
        for f in sorted(s)[:40]: o.write(f'{t}\t{f}\n')
print('rows',len(rows),'cited',len(C))
P
rm -rf $W; date
