#!/usr/bin/env python3
# usage: frame_chain_calfix_cut.py <slice_top.sv> <json rows from frame_chain_calendar.py>  (CANDIDATE die fix, bench cut only)
# Candidate die-calendar fix v2 (TOKc-S81b 10-22): delay ONLY the chained frame's rst_n by `delay` reset stations on the
# frame's ck_r0 (the leaf, its derived ret-lane hop-0 gates and the slice-side landings keep their calendar: the ret
# lanes carry bubbles until the frame releases).  v1 (delay the whole leaf) moved the ret-lane gates and faulted the
# slice-side ret landings ld_r_f_<frame> (land_fault).
import re,sys,json
sv=sys.argv[1]; rows=json.loads(sys.argv[2]); t=open(sv).read(); done=[]
for inst,r in rows.items():
    d=r['delay']; n=r['rst']
    if d<=0: continue
    m=re.search(r'(col_\w+ #\(\.INSTANCE\("%s"\)\) %s \(.*?)\.rst_n\(%s\)'%(inst,inst,re.escape(n)),t,re.S)
    if not m: raise SystemExit(f'{inst}: .rst_n({n}) not found')
    ck=re.search(r'\.ck_r0\(([\w\[\]]+)\)',m.group(1)).group(1)
    cell=re.search(r'(dsfd_rly_1_\w+) \S+ \(\.ck\([^)]*\), \.rs\([^)]*\), \.i\([^)]*\), \.o\(%s\)\);'%re.escape(n),t)
    cell=cell.group(1) if cell else 'dsfd_rly_1_WN'
    t=t[:m.end()-len(f'.rst_n({n})')]+f'.rst_n({n}__fr{d})'+t[m.end():]
    add=[]; prev=n
    for k in range(1,d+1):
        o=f'{n}__fr{k}'; add.append(f'  wire {o};\n  {cell} st_{o} (.ck({ck}), .rs({prev}), .i({prev}), .o({o}));   // TOKc-S81b candidate die-calendar fix v2: chained frame {inst} rst_n +{d}')
        prev=o
    i=t.rfind('\nendmodule',0,t.find('module dv_flight_sim') if 'module dv_flight_sim' in t else len(t))
    t=t[:i]+'\n'+'\n'.join(add)+t[i:]
    done.append((inst,n,d,ck))
open(sv,'w').write(t); print(json.dumps(done))
