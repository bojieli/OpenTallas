#!/usr/bin/env python3
"""Build fresh separated gated/ungated CTS clusters from current placed parent sinks."""
import json, statistics as S, sys
from pathlib import Path

def clusters(src):
    sinks = {0: [], 1: []}; macros = []; kids = []
    for line in Path(src).read_text().splitlines():
        p = line.split()
        if p[0] == 'DIE': W, H, dbu = map(float,p[1:])
        elif p[0] == 'MACRO': macros.append([float(v)/dbu for v in p[1:]])
        elif p[0] == 'SINK':
            name,master,pin,x,y,ung,block = p[1:]
            q = (name,float(x)/dbu,float(y)/dbu)
            if int(block): kids.append(dict(inst=name,module=master,pin=list(q[1:]),clock_pin=pin))
            else: sinks[int(ung)].append(q)
    W/=dbu; H/=dbu
    def bbox(a):return [min(q[1] for q in a), min(q[2] for q in a), max(q[1] for q in a), max(q[2] for q in a)]
    def overlap(b):return any(min(b[2],m[2])-max(b[0],m[0])>10 and min(b[3],m[3])-max(b[1],m[1])>10 for m in macros)
    def split(a):
        b=bbox(a); ex=[b[2]-b[0],b[3]-b[1]]
        if (max(ex)<=190 and len(a)<=1024 and not overlap(b)) or len(a)<=1:return [a]
        ax=1 if ex[0]>=ex[1] else 2; a=sorted(a,key=lambda q:(q[ax],q[0])); mid=len(a)//2
        return split(a[:mid])+split(a[mid:])
    def legal(x,y):
        x=min(max(x,6),W-6);y=min(max(y,6),H-6)
        inside=lambda a,b:any(m[0]-1<a<m[2]+1 and m[1]-1<b<m[3]+1 for m in macros)
        if not inside(x,y):return [x,y]
        pts=[]
        for m in macros:
            pts += [(m[0]-1.5,y),(m[2]+1.5,y),(x,m[1]-1.5),(x,m[3]+1.5)]
        pts=[p for p in pts if 6<=p[0]<=W-6 and 6<=p[1]<=H-6 and not inside(*p)]
        if not pts:raise ValueError('no legal cluster root')
        return list(min(pts,key=lambda p:abs(p[0]-x)+abs(p[1]-y)))
    cs=[]
    for ung,a in sinks.items():
        if not a:continue
        for group in split(a):
            root=legal(S.median(q[1] for q in group),S.median(q[2] for q in group))
            cs.append(dict(name='a0cl'+str(len(cs)),root=root,box=bbox(group),regs=[q[0] for q in group],ungated=bool(ung),n=len(group)))
    if not sinks[0] or not sinks[1]:raise ValueError('parent needs both gated and ungated real clock sinks')
    return dict(W=W,H=H,macros=macros,kids=kids,clusters=cs)

def prepare(src,out):
    d=clusters(src);Path(out).write_text(json.dumps(d,indent=1)+'\n')
    with Path(out).with_suffix('.tcl').open('w') as f:
        f.write('set CL {}\n')
        for c in d['clusters']:
            f.write('lappend CL [list %s %.6f %.6f %s {%s}]\n'%(c['name'],*c['root'],int(c['ungated']),' '.join('{%s}'%r for r in c['regs'])))
    print('PARENT clusters',len(d['clusters']),'regs',sum(c['n'] for c in d['clusters']),'kids',len(d['kids']))

if __name__=='__main__':prepare(*sys.argv[1:])
