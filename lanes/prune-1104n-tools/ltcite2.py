#!/usr/bin/env python3
# PRUNE-1104N: split ltcite rows by what the citer really is, full path only. usage: ltcite2.py list.txt cited.tsv out.txt  ; out.txt = rows a build input cites (hold). Others go; COORD 10:49: only a live job or spec holds, and those are checked in ltclass.py. A build input held here is stricter than the ruling, on purpose.
import sys,re,os,collections
L,C,O=sys.argv[1:4]; rows=set(l.strip() for l in open(L))
INPUT=re.compile(r'(\.f|\.sh|\.tcl|\.mk|\.env|\.sdc|\.cfg|\.yaml|\.yml|\.py|\.manifest|Makefile|kit_rtl[^/]*\.json|config[^/]*\.json|spec[^/]*\.json|job[^/]*\.json|bind[^/]*\.json)$')
R='/srv/opentallas-scratch2/claude/'
hold={};kept=collections.Counter();why=collections.Counter()
for l in open(C):
    t,f=l.rstrip('\n').split('\t')
    if any(f.startswith(x+'/') for x in (t,)): continue
    rel=t[len('/srv/opentallas-scratch2/'):]
    try: s=open(f,errors='replace').read()
    except OSError: continue
    # full-path citation only; a same-named event under another root is not this row. Hostname-qualified other-host paths count as not this row.
    hit=[m for m in re.finditer(r'([\w-]+:)?/srv/opentallas-scratch2?/'+re.escape(t[len(R)-7:]),s) if not (m.group(1) and m.group(1)[:-1] not in(os.uname().nodename,sys.argv[4] if len(sys.argv)>4 else ''))]
    if not hit: why['other-root-or-host']+=1; continue
    if any(f.startswith(x+'/') for x in rows): why['citer-also-on-list']+=1; continue
    if INPUT.search(f): hold.setdefault(t,f); why['input']+=1
    else: why['evidence:'+os.path.basename(f)[:28]]+=1
with open(O,'w') as o:
    for t,f in hold.items(): o.write(f'{t}\t{f}\n')
print('hold',len(hold),'of',len(rows),dict(why.most_common(14)))
