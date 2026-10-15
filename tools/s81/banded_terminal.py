#!/usr/bin/env python3
"""Split a banded terminal register stage spatially without adding a cycle.

Geometry only: the emitted die glue remains real, one common-clock register per
bit. Native views, clock insertion and route qualification are separate gates.
"""
import math

def propose(A, B, oldQ, obstacles, old_name, thickness, pa, gx=.432, gy=2.16,
            inset=.048, reach=450.0, band_gap=20.0):
    """Horizontal R0 stage, inputW/outputE, facing a hard W input.

    Return disjoint contiguous bit slices. Every outgoing hard-ended bit is no
    longer, and each incoming station hop is rejudged against cut and reach.
    """
    if not A or len(A) != len(B) or len(B) != len(oldQ):
        return None
    if any(q is None for q in A+B+oldQ) or any(q[2] != 'W' for q in B):
        return None
    groups = []
    for i in sorted(range(len(B)), key=lambda j:B[j][1]):
        if not groups or B[i][1]-B[groups[-1][-1]][1] > band_gap:
            groups.append([])
        groups[-1].append(i)
    if len(groups) <= 1:
        return None
    # The bus renderer supports contiguous slices. Retain each bit's identity,
    # including the reversed lane-group ordering within one physical band.
    groups = sorted((sorted(g) for g in groups),key=min)
    if any(g != list(range(min(g), max(g)+1)) for g in groups):
        return None
    ans = []
    def ceilgrid(x,g):return math.ceil((x-1e-9)/g)*g
    for g in groups:
        lo,hi=min(g),max(g)
        y0=math.floor((min(B[i][1] for i in g)-.2)/gy)*gy
        height=max(17.28,ceilgrid(max(B[i][1] for i in g)+.2-y0,gy))
        found=None
        # Start beside the hard face, retreat only as needed to clear the
        # stations in the empty spaces between the load's data bands.
        edge=min(B[i][0] for i in g)-.096
        xbase=math.floor((edge-thickness-.048)/gx)*gx
        for k in range(200):
            x=xbase-k*gx; box=(x,y0,thickness,height)
            if any(o[0]!=old_name and x<o[1]+o[3]-1e-6 and x+thickness>o[1]+1e-6
                   and y0<o[2]+o[4]-1e-6 and y0+height>o[2]+1e-6 for o in obstacles):
                continue
            if any(x<t['x']+t['w']-1e-6 and x+thickness>t['x']+1e-6
                   and y0<t['y']+t['h']-1e-6 and y0+height>t['y']+1e-6 for t in ans):
                continue
            Di=[(x+inset+.096,B[i][1],'W','M4') for i in g]
            Dq=[(x+thickness-inset-.096,B[i][1],'E','M4') for i in g]
            Ai=[A[i] for i in g];Bi=[B[i] for i in g]
            Lin=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(Ai,Di)]
            Lout=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(Dq,Bi)]
            old=[abs(oldQ[i][0]-B[i][0])+abs(oldQ[i][1]-B[i][1]) for i in g]
            if max(Lin)>reach+1e-6 or any(n>o+1e-6 for n,o in zip(Lout,old)):
                continue
            pi,po=pa.bundle(Ai,Di),pa.bundle(Dq,Bi)
            if pi['verdict']=='FAIL' or po['verdict']=='FAIL':
                continue
            found=dict(lo=lo,hi=hi,x=round(x,6),y=round(y0,6),w=thickness,h=height,
                       along=[round(B[i][1]-y0,6) for i in g],
                       input_max_um=max(Lin),output_max_um=max(Lout),
                       input_cut=pi['jog_cut'],output_cut=po['jog_cut'],
                       hard_bit_lengths_never_grow=True)
            break
        if found is None:return None
        ans.append(found)
    assert sum(q['hi']-q['lo']+1 for q in ans)==len(B)
    return ans

def apply(G, m, it, proposal, incoming, outgoing):
    """Rewire exactly one terminal stage into the proposed parallel bands."""
    in_id,in_cls,bits,in_eps=incoming
    out_id,out_cls,out_bits,out_eps=outgoing
    assert len(in_eps)==len(out_eps)==2 and bits==out_bits
    assert in_eps[1]==(it.name,'di') and out_eps[0]==(it.name,'dq')
    def sub(port,lo,hi):
        base,start,_=G.pslice(port)
        off=start or 0
        return f'{base}[{off+lo}:{off+hi}]'
    spread=m.setdefault('spread_stations',{})
    children=[]
    for j,p in enumerate(proposal):
        n=p['hi']-p['lo']+1
        master=f'dsfd_hstnh_{n}_sp{len(spread)}'
        child=G.Inst(f'{it.name}_b{j}',master,p['x'],p['y'],p['w'],p['h'],
                     orient='R0',kind='hstn',region=it.region,domain=it.domain,
                     power_w=it.power_w*n/bits)
        children.append(child)
        spread[master]=dict(along=p['along'],horiz=True,out_face='E',orient='R0')
        m['pdir'][master]=dict(ck=('input',1),di=('input',n),dq=('output',n))
    buses=[]
    for bus in m['buses']:
        bid,cls,width,eps=bus
        if bid==in_id:
            for j,(child,p) in enumerate(zip(children,proposal)):
                buses.append((f'{bid}_band{j}',cls,p['hi']-p['lo']+1,
                              [(eps[0][0],sub(eps[0][1],p['lo'],p['hi'])),(child.name,'di')]))
        elif bid==out_id:
            for j,(child,p) in enumerate(zip(children,proposal)):
                buses.append((f'{bid}_band{j}',cls,p['hi']-p['lo']+1,
                              [(child.name,'dq'),(eps[1][0],sub(eps[1][1],p['lo'],p['hi']))]))
        elif any(n==it.name for n,_ in eps):
            assert all(p=='ck' for n,p in eps if n==it.name),bus
            ee=[]
            for e in eps:
                ee.extend([(ch.name,'ck') for ch in children] if e[0]==it.name else [e])
            buses.append((bid,cls,width,ee))
        else:buses.append(bus)
    m['buses']=buses
    m['insts']=[i for i in m['insts'] if i.name!=it.name]+children
    if '_by' in m:m['_by']={i.name:i for i in m['insts']}
    m.setdefault('station_band_splits',{})[it.name]=dict(
        original_bits=bits,children=[dict(name=c.name,master=c.master,**p) for c,p in zip(children,proposal)],
        cycle_delta=0,register_bits_before=bits,register_bits_after=sum(p['hi']-p['lo']+1 for p in proposal),
        clock_root_delta=len(children)-1,
        qualification='GEOMETRY_ONLY: actual glue equivalence/native views, phi-R, CTS, TT/FF/DRC remain required')
    return children
