#!/usr/bin/env python3
# usage: frame_chain_calfix_cut.py <slice_top.sv> x <json rows from frame_chain_calendar.py>  (CANDIDATE die fix applied to a bench cut only)
# Candidate die-calendar fix (TOKc-S81b 10-22): a chained frame (x lanes clocked by the upstream frame's xok) must not
# release before its lane clock starts: add delay = G_up - R0 reset stations (same dsfd_rly_1 cell / clock as the
# leaf's last station) after the frame's reset leaf, so the frame AND everything derived from its leaf shift together.
import re,sys,json,subprocess
sv=sys.argv[1]; rec=json.loads(subprocess.run([sys.executable,sys.argv[2],sv],capture_output=True,text=True).stdout.strip().split('\n')[-1]) if False else None
t=open(sv).read()
import importlib.util
rows=json.loads(sys.argv[3])
done=[]
for inst,r in rows.items():
    d=r['delay']; n=r['rst']
    if d<=0: continue
    m=re.search(r'(\n\s*)(dsfd_rly_1_\w+) (\S+) \(\.ck\(([\w\[\]]+)\), \.rs\((\w+)\), \.i\((\w+)\), \.o\(%s\)\);'%re.escape(n),t)
    if not m: raise SystemExit(f'no station driving {n}')
    ind,cell,sname,ck,rs,i=m.groups()
    new=f'{ind}{cell} {sname} (.ck({ck}), .rs({rs}), .i({i}), .o({n}__cal0));'
    prev=f'{n}__cal0'; decl=[f'{ind}wire {n}__cal0;']
    for k in range(1,d+1):
        o=n if k==d else f'{n}__cal{k}'
        if k<d: decl.append(f'{ind}wire {o};')
        new+=f'{ind}{cell} {sname}__cal{k} (.ck({ck}), .rs({prev}), .i({prev}), .o({o}));   // TOKc-S81b candidate die-calendar fix: chained frame {inst} released {d} later'
        prev=o
    t=t[:m.start()]+''.join(decl)+new+t[m.end():]
    done.append((inst,n,d))
open(sv,'w').write(t); print(json.dumps(done))
