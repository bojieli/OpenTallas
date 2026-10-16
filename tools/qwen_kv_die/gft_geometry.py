#!/usr/bin/env python3
"""Exact connected placement alternatives over realized KV11 pins and nets.

No RTL or cycle changes, source-only geometry candidate, no route qualification.
Every affected data net is expanded from actual die.v (including its concat bit
order), then every endpoint is transformed from the actual LEF/placed DEF.
Clock endpoints are reported separately; this model cannot qualify their tree.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
import kvsys_classify as C


ALTS = {
    **{f'balanced_{x:g}':dict(gx=x,near_row=1,far_row=2,t2x=x-351,t1x=x-351,t1row=1,t2row=2,s1x=x+351,s2x=x+351,s1row=2,s2row=1) for x in (324.0,394.2,405.864,409.32)},
    'stack_near_first': dict(gx=226.8, near_row=1, far_row=2, t2x=-216.0),
    'stack_far_first': dict(gx=226.8, near_row=2, far_row=1, t2x=-216.0),
    'stack_shifted54': dict(gx=172.8, near_row=1, far_row=2, t2x=-162.0),
}


def bits(expr, widths):
    parts=expr.strip('{}').split(',') if expr.startswith('{') else [expr]
    out=[]
    for p in reversed(parts):
        p=p.strip();m=re.fullmatch(r'(\S+)\[(\d+)(?::(\d+))?\]',p)
        if m:
            hi=int(m[2]);lo=int(m[3] or m[2]);out.extend(f'{m[1]}[{i}]' for i in range(lo,hi+1))
        else:out.extend(f'{p}[{i}]' for i in range(widths.get(p,1)))
    return out


def case_graph(case,tags):
    text=(case/'die.v').read_text();widths={}
    for m in re.finditer(r'\bwire\s+(?:\[(\d+):0\]\s+)?(\S+);',text):widths[m[2]]=int(m[1])+1 if m[1] else 1
    pins,sizes=C.lef_pins([case/'elements.lef']);dirs={};cur=pin=None
    for line in (case/'elements.lef').open():
        t=line.split()
        if not t:continue
        if t[0]=='MACRO':cur=t[1];dirs.setdefault(cur,{})
        elif t[0]=='PIN':pin=t[1]
        elif t[0]=='DIRECTION' and cur and pin:dirs[cur][pin]=t[1]
        elif t[0]=='END' and len(t)>1 and t[1]==pin:pin=None
    pos=C.placed_def(case/'floorplan_placed.def')
    inst={};connections={};affected=set()
    for m in re.finditer(r'^\s*(\w+)\s+(\S+)\s*\((.*?)\);',text,re.M):
        master,name,body=m.groups()
        if name not in pos or master not in pins:continue
        inst[name]=master
        connections[name]=[(q[1].lstrip('\\'),q[2].strip()) for q in re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)',body)]
        if any(re.fullmatch(r'hst_'+t+r'_[0-3]_(g|t1|t2|s1|s2)',name) or re.fullmatch(r'head_'+t+r'_[12]__u_ftg',name) for t in tags):affected.add(name)
    selected=set()
    for n in affected:
        for port,expr in connections[n]:
            if port not in ('ck','clk','rst_n'):selected.update(bits(expr,widths))
    bases={re.sub(r'\[.*','',n) for n in selected}
    nets=collections.defaultdict(list);clock=[];missing=[]
    for name,conns in connections.items():
        pp=pins[inst[name]]
        for port,expr in conns:
            if port in ('ck','clk','rst_n'):
                if name in affected:clock.append(dict(instance=name,port=port if port in pp else port+'[0]',net=expr))
                continue
            base=re.sub(r'\[.*','',expr)
            # Avoid expanding unrelated 8k-bit memory ports.
            if not any(tok in bases for tok in re.findall(r'[A-Za-z_][A-Za-z0-9_$]*',expr)):continue
            for i,net in enumerate(bits(expr,widths)):
                if net not in selected:continue
                pin=port if port in pp else f'{port}[{i}]'
                if pin not in pp:missing.append((name,pin,net));continue
                nets[net].append((name,pin))
    if missing:raise ValueError(f'missing actual named LEF pins: {missing[:5]}')
    return dict(pins=pins,dirs=dirs,sizes=sizes,pos=pos,inst=inst,nets=nets,affected=affected,clocks=clock)


def proposal(g,tags,name):
    p=dict(g['pos']);moves={}
    if name=='baseline':return p,moves
    a=ALTS[name]
    def shift(n,dx,dy):
        if n not in p:return
        x,y,o=p[n];p[n]=(round(x+dx,6),round(y+dy,6),o);moves[n]=dict(old=g['pos'][n],new=p[n],delta_um=[dx,dy])
    for t in tags:
        sx=-1 if p['ectl_'+t+'__u_a'][2] in ('FN','S','MY','R180') else 1
        for near,far,sy in [(1,0,-1),(2,3,1)]:
            for h,oldx,row in [(near,54,a['near_row']),(far,405,a['far_row'])]:
                shift(f'hst_{t}_{h}_g',sx*(a['gx']-oldx),sy*43.2*(row-1))
            shift(f'hst_{t}_{near}_t2',sx*(a['t2x']-135),sy*43.2*(a.get('t2row',1)-2))
            shift(f'hst_{t}_{near}_t1',sx*(a.get('t1x',-216)+216),sy*43.2*(a.get('t1row',2)-2))
            # T1 stays at x-216,row2; score returns move into newly freed row1.
            shift(f'hst_{t}_{near}_s1',sx*(a.get('s1x',594)-480.6),sy*43.2*(a.get('s1row',1)-2))
            shift(f'hst_{t}_{near}_s2',sx*(a.get('s2x',653.4)-540),sy*43.2*(a.get('s2row',1)-2))
            # A single2.16um move stays fully inside the declared y189..216 FT channel.
            shift(f'head_{t}_{near}__u_ftg',0,-sy*2.16)
    return p,moves


def point(g,p,n,pin):return C.pin_world(g['pins'][g['inst'][n]][pin],p[n][:2],g['sizes'][g['inst'][n]],p[n][2])


def evaluate(g,p,moves):
    groups={};worst=[];over=0;edges=0;netspan=[]
    for net,ends in g['nets'].items():
        if len(ends)<2:continue
        pts=[point(g,p,*e) for e in ends]
        hpwl=max(q[0] for q in pts)-min(q[0] for q in pts)+max(q[1] for q in pts)-min(q[1] for q in pts)
        netspan.append((round(hpwl,6),net,len(ends)))
        for i,(na,pa) in enumerate(ends):
            for j in range(i+1,len(ends)):
                na,pa=ends[i];nz,pz=ends[j]
                # Input-input pair still matters for multicast span, but not a pipeline edge.
                oa=g['dirs'][g['inst'][na]][pa]=='OUTPUT'
                oz=g['dirs'][g['inst'][nz]][pz]=='OUTPUT'
                if oa==oz:continue
                if oz:na,pa,nz,pz=nz,pz,na,pa
                d=abs(pts[i][0]-pts[j][0])+abs(pts[i][1]-pts[j][1]);edges+=1;over+=d>500+1e-6
                key=(re.sub(r'\[.*','',na),re.sub(r'\[.*','',nz),re.sub(r'\[.*','',pz))
                old=groups.get(key)
                if old is None or d>old['max_um']:groups[key]=dict(launch=na,capture=nz,port=re.sub(r'\[.*','',pz),max_um=round(d,6),example=[net,pa,pz])
    # Full realized component rectangle collisions; only changed incidents count.
    collisions=[];gaps=[]
    for n in moves:
        x,y,_=p[n];w,h=g['sizes'][g['inst'][n]]
        for q,(qx,qy,_) in p.items():
            if q==n or q not in g['inst'] or (q in moves and q<n):continue
            qw,qh=g['sizes'][g['inst'][q]];ix=min(x+w,qx+qw)-max(x,qx);iy=min(y+h,qy+qh)-max(y,qy)
            if ix>1e-5 and iy>1e-5:collisions.append(dict(a=n,b=q,overlap_um=[round(ix,6),round(iy,6)]))
            elif ix>0 and 0<=-iy<20-1e-5:gaps.append(dict(a=n,b=q,gap_um=round(-iy,6)))
            elif iy>0 and 0<=-ix<20-1e-5:gaps.append(dict(a=n,b=q,gap_um=round(-ix,6)))
    return dict(data_edges=edges,over500_edges=over,worst_groups=sorted(groups.values(),key=lambda r:-r['max_um']),worst_multicast_hpwl=sorted(netspan,reverse=True)[:12],collisions=collisions,under20um_gaps=gaps,moves=moves,clock_incidents=[dict(r,old_um=point(g,g['pos'],r['instance'],r['port']),new_um=point(g,p,r['instance'],r['port'])) for r in g['clocks'] if r['instance'] in moves],qualification=dict(physical=False,clock_tree=False,route=False,static_cycles_changed=False))


def draw(g,p,tags,out,name,r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axs=plt.subplots(1,len(tags),figsize=(10*len(tags),12),squeeze=False)
    for ax,t in zip(axs[0],tags):
        names=[n for n in p if n in g['inst'] and (n.startswith('ectl_'+t+'__') or n.startswith('hst_'+t+'_') or n.startswith('head_'+t+'_'))]
        for n in names:
            x,y,_=p[n];w,h=g['sizes'][g['inst'][n]];col='#9ecae1' if n.startswith('hst') or n.endswith('ftg') else ('#a1d99b' if n.startswith('ectl') else '#fdd0a2')
            ax.add_patch(Rectangle((x,y),w,h,fc=col,ec='crimson' if n in r['moves'] else 'gray',lw=1 if n in r['moves'] else .5,alpha=.7))
            if n in r['moves'] or n.startswith('ectl'):ax.text(x+w/2,y+h/2,n.replace(t+'_','').replace('__u_','/'),fontsize=6,ha='center',va='center')
        for row in r['worst_groups']:
            if row['launch'] not in names or row['capture'] not in names:continue
            _,a,z=row['example'];pt=point(g,p,row['launch'],a);qt=point(g,p,row['capture'],z)
            ax.plot([pt[0],qt[0]],[pt[1],qt[1]],color='crimson' if row['max_um']>500 else '#2171b5',lw=.55,alpha=.65)
        ax.autoscale();ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(t+' actual named pins / candidate realized origins');ax.set_xlabel('um');ax.set_ylabel('um')
    fig.suptitle(f'{name}: {r["over500_edges"]} data edges >500um; {len(r["collisions"])} moved-component collisions\nAll incident data nets, same leaves/cycles; HPWL estimate only, clocks/package/route OPEN')
    fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=150);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--tags',nargs='+',default=['WS_4','WN_1']);ap.add_argument('--all',action='store_true');ap.add_argument('--ranked-only',action='store_true');ap.add_argument('--no-images',action='store_true');a=ap.parse_args();
    if a.all:a.tags=sorted(set(re.findall(r'qkd_ectl_a_tp8_epoch_direct ectl_(\w+)__u_a', (a.case/'die.v').read_text())))
    a.out.mkdir(parents=True,exist_ok=True)
    g=case_graph(a.case,a.tags);summary={}
    for name in ['baseline',*[n for n in ALTS if not a.ranked_only or n.startswith('balanced_')]]:
        p,m=proposal(g,a.tags,name)
        if name=='baseline':m={n:dict(old=g['pos'][n],new=g['pos'][n],delta_um=[0,0]) for n in g['affected']}
        r=evaluate(g,p,m);summary[name]=r
        (a.out/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
        if not a.no_images:draw(g,p,[t for t in ['WS_4','WN_1'] if t in a.tags] or a.tags[:2],a.out,name,r)
        print(name,'edges',r['data_edges'],'over500',r['over500_edges'],'collisions',len(r['collisions']),'max',r['worst_groups'][0]['max_um'])
    ledger=dict(scope='SOURCE_GEOMETRY_CANDIDATES_ONLY',sources={str(a.case/n):hashlib.sha256((a.case/n).read_bytes()).hexdigest() for n in ['die.v','elements.lef','floorplan_placed.def']},pin_basis='Actual named first LEF RECT centres transformed by realized DEF orientation; all actual die.v bit assignments',tags=a.tags,affected_instances=len(g['affected']),affected_data_nets=len(g['nets']),clock_tree_qualification=False,source_cycles_changed=False)
    (a.out/'provenance.json').write_text(json.dumps(ledger,indent=2)+'\n')


if __name__=='__main__':main()
