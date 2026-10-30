"""Model-only native flat clock forest. No placement/CTS/STA measurements consumed.

Exact sink geometry is a structural inventory, not a timing qualification. Plans
remain held until the TT/FF model, reviewed legal placement and native gates pass.
"""
import argparse, gzip, hashlib, json, math, re
from collections import Counter, defaultdict
from pathlib import Path
import die_clock_128 as LIB
import core_infra_plan as RC

# Exact per-class clock placement RC from setRC_rcx_asap7.tcl. No NDR discount.
R=.0214161
C=.113298


def inventory(path):
    cells={}; ports={}; nets=[]; outline=None
    for line in Path(path).read_text().splitlines():
        r=line.split('\t')
        if r[0]=='D':outline=list(map(float,r[1:]))
        elif r[0]=='C':
            rect=list(map(float,r[4:8]));cells[r[1]]=dict(id=r[1],name=r[8],master=r[3],kind=r[2],xy=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],rect=rect)
        elif r[0]=='P':ports[r[1]]=dict(name=r[2],io=r[3],signal=r[4],xy=list(map(float,r[6:8])))
        elif r[0]=='N' and r[1]=='CLOCK':nets.append(r[2:])
    roots={}; owned={}
    for net in nets:
        source=net[0]
        sinks=[q[1:-1] for q in net[1:] if q.startswith('i') and q.endswith('c') and q[1:-1] in cells]
        if not sinks:continue
        if not source.startswith('p'):raise ValueError('preCTS native inventory requires direct known input clock roots')
        root=ports[source[1:]]['name']
        roots[root]=dict(port=source[1:],sinks=sinks,other_loads=[q[1:] for q in net[1:] if q.startswith('i') and not q.endswith('c') and q[1:] in cells])
        for q in sinks:
            if q in owned:raise ValueError('clock root alias')
            owned[q]=root
    seq={k for k,v in cells.items() if v['kind']=='S'}
    if set(owned)!=seq:raise ValueError(f'incomplete native sequential clock inventory: missing{len(seq-set(owned))}')
    return dict(schema='opentallas.flat_clock_inventory.v1',geometry_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),outline=outline,cells=cells,ports=ports,roots=roots)


def overlay_endpoints(inv, path, module):
    """Analytical overlay only; final qualification needs the complete legal ODB dump."""
    packet=json.loads(Path(path).read_text())
    outline=[inv['outline'][2]-inv['outline'][0],inv['outline'][3]-inv['outline'][1]]
    if packet.get('schema')!='opentallas.ft_full_stage.v1' or packet.get('module')!=module or packet.get('outline_um')!=outline:
        raise ValueError('endpoint overlay stale module/outline/schema')
    byname={c['name']:c for c in inv['cells'].values() if c['kind']=='S'};seen=set()
    for name,slot in packet['slots'].items():
        targets=slot['targets'];expected={(j,b) for j in range(slot['stations']) for b in range(slot['width']+1)}
        if len(targets)!=len(expected) or {(r['stage'],r['bit']) for r in targets}!=expected:raise ValueError('endpoint overlay incomplete stage-bit inventory')
        for r in targets:
            if r['name'] in seen or r['name'] not in byname:raise ValueError('endpoint overlay missing/aliased actual FF')
            seen.add(r['name']);c=byname[r['name']]
            if r['master']!=c['master'] or any(abs(r['size'][i]-(c['rect'][i+2]-c['rect'][i]))>0.001 for i in (0,1)):
                raise ValueError('endpoint overlay stale actual master/footprint')
            x,y=r['xy'];w,h=r['size'];c['rect']=[x,y,x+w,y+h];c['xy']=[x+w/2,y+h/2]
    inv['endpoint_overlay']=dict(source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),targets=len(seen),module=module,
                                  qualified=False,basis='exact target overlay; complete successor legalized geometry still required')
    return inv


def structural_pairs(path, inv):
    """Conservative actual data/reset connectivity; clock edges excluded.

    geom.tsv does not distinguish asynchronous reset from D at a capture, so
    these include extra reset relationships. They may fail conservatively, never
    silently claim a STA-exact exception.
    """
    comb={q for q,c in inv['cells'].items() if c['kind']!='S'}
    preds={q:set() for q in inv['cells']};children=defaultdict(set);indegree={q:0 for q in comb}
    captures=defaultdict(set)
    for line in Path(path).read_text().splitlines():
        r=line.split('\t')
        if r[0]!='N' or r[1]=='CLOCK' or not r[2].startswith('i'):continue
        source=r[2][1:]
        if source not in inv['cells']:continue
        for sink in r[3:]:
            if not sink.startswith('i') or sink.endswith('c'):continue
            target=sink[1:]
            if target not in inv['cells']:continue
            if target in comb:
                if source in comb:
                    if target not in children[source]:children[source].add(target);indegree[target]+=1
                else:preds[target].add(source)
            elif source in comb:captures[target].add(source)
            else:preds[target].add(source)
    from collections import deque
    todo=deque(q for q,n in indegree.items() if not n);count=0
    while todo:
        q=todo.popleft();count+=1
        for target in children[q]:
            preds[target].update(preds[q]);indegree[target]-=1
            if not indegree[target]:todo.append(target)
    if count!=len(comb):raise ValueError('combinational cycle prevents complete structural clock relation extraction')
    for target,sources in captures.items():
        for source in sources:preds[target].update(preds[source])
    return [(source,target) for target,c in inv['cells'].items() if c['kind']=='S' for source in sorted(preds[target])]


def assign(inv,cap=1500):
    taps={p['name']:p['xy'] for p in inv['ports'].values() if re.fullmatch(r'clk(?:_t[0-9]+)?',p['name'])}
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    primary=list(inv['roots']['clk']['sinks']);groups={k:[] for k in taps}
    bins=defaultdict(list)
    for q in primary:
        xy=inv['cells'][q]['xy'];bins[int(xy[0]//10),int(xy[1]//10)].append(q)
    buckets=list(bins.values());names=list(taps);n=len(buckets);m=len(names)
    costs=[]
    for ids in buckets:
        xy=[sum(inv['cells'][q]['xy'][a] for q in ids)/len(ids) for a in (0,1)]
        costs.extend(sum(abs(a-b) for a,b in zip(xy,taps[name]))**2 for name in names)
    eq=lil_matrix((n,n*m));ub=lil_matrix((m,n*m))
    for i in range(n):
        eq[i,i*m:(i+1)*m]=1
        for j in range(m):ub[j,i*m+j]=1
    fit=linprog(np.array(costs),A_ub=ub.tocsr(),b_ub=np.full(m,cap),A_eq=eq.tocsr(),b_eq=np.array([len(q) for q in buckets]),bounds=(0,None),method='highs')
    if not fit.success:raise ValueError('primary distance/load transport infeasible: '+fit.message)
    allocation=np.rint(fit.x).astype(int).reshape(n,m)
    for ids,counts in zip(buckets,allocation):
        if sum(counts)!=len(ids):raise ValueError('nonintegral transport inventory')
        todo=sorted(ids)
        for name,count in zip(names,counts):
            # Use nearest exact actual points within each10um bin allocation.
            todo.sort(key=lambda q:(sum(abs(a-b) for a,b in zip(inv['cells'][q]['xy'],taps[name])),q))
            groups[name].extend(todo[:count]);todo=todo[count:]
    for root,record in inv['roots'].items():
        if root!='clk':groups[root]=list(record['sinks'])
    return groups


def topology(inv,groups,max_leg=150,leaf_cap=32,leaf_radius=100):
    nodes=[];roots={}
    point=lambda q:inv['cells'][q]['xy']
    def add(root,xy,children=None,sinks=None):
        n=len(nodes);nodes.append(dict(name=f'ot_flat_clk_{n}',root=root,xy=xy,children=children or [],sinks=sinks or [],master='BUFx24_ASAP7_75t_R'));return n
    def branch(root,ids):
        xy=[(min(point(q)[a] for q in ids)+max(point(q)[a] for q in ids))/2 for a in (0,1)]
        radius=max(sum(abs(a-b) for a,b in zip(xy,point(q))) for q in ids)
        if len(ids)<=leaf_cap and radius<=leaf_radius:return add(root,xy,sinks=ids)
        axis=max((0,1),key=lambda a:max(point(q)[a] for q in ids)-min(point(q)[a] for q in ids))
        ids=sorted(ids,key=lambda q:(point(q)[axis],q));mid=xy[axis]
        m=sum(point(q)[axis]<mid for q in ids)
        if m==0 or m==len(ids):m=len(ids)//2
        if not m:return add(root,xy,sinks=ids)
        kids=[branch(root,ids[:m]),branch(root,ids[m:])]
        return add(root,xy,children=kids)
    ports={p['name']:p['xy'] for p in inv['ports'].values()}
    for root,ids in groups.items():
        if not ids:continue
        tree=branch(root,ids);entry=add(root,ports[root],children=[tree]);roots[root]=entry
    # Add only distance-required repeaters on shortest Manhattan routes.
    for n in list(nodes):
        out=[]
        for kid in n['children']:
            a,b=n['xy'],nodes[kid]['xy'];dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1]);length=dx+dy
            segments=max(1,math.ceil(length/max_leg));prev=None;first=kid
            for j in range(1,segments):
                t=length*j/segments
                xy=[a[0]+math.copysign(min(t,dx),b[0]-a[0]),a[1]+math.copysign(max(0,t-dx),b[1]-a[1])]
                new=add(n['root'],xy)
                if prev is None:first=new
                else:nodes[prev]['children']=[new]
                prev=new
            if prev is not None:nodes[prev]['children']=[kid]
            out.append(first)
        n['children']=out
    return nodes,roots


def topology_h(inv,groups):
    """Fixed geometric binary H-tree layers per primary grid region.

    Pruning removes only branches with no actual assigned sink. Each occupied
    terminal uses parallel local drivers of <=32 real FF clock pins. Different
    local cell density never adds a stage to the primary tree.
    """
    nodes=[];roots={};ports={p['name']:p['xy'] for p in inv['ports'].values()}
    taps={n:xy for n,xy in ports.items() if re.fullmatch(r'clk(?:_t[0-9]+)?',n)}
    xs=sorted(set(xy[0] for xy in taps.values()));ys=sorted(set(xy[1] for xy in taps.values()));die=inv['outline']
    def add(root,xy,kids=None,sinks=None):
        k=len(nodes);nodes.append(dict(name=f'ot_flat_clk_{k}',root=root,xy=list(xy),children=kids or [],sinks=sinks or [],master='BUFx24_ASAP7_75t_R'));return k
    def chunks(ids):
        xy=[(min(inv['cells'][q]['xy'][a] for q in ids)+max(inv['cells'][q]['xy'][a] for q in ids))/2 for a in (0,1)]
        radius=max(sum(abs(a-b) for a,b in zip(xy,inv['cells'][q]['xy'])) for q in ids)
        if len(ids)<=32 and radius<=40:return [(xy,ids)]
        axis=max((0,1),key=lambda a:max(inv['cells'][q]['xy'][a] for q in ids)-min(inv['cells'][q]['xy'][a] for q in ids));ids=sorted(ids,key=lambda q:inv['cells'][q]['xy'][axis]);m=len(ids)//2
        return chunks(ids[:m])+chunks(ids[m:])
    def build(root,ids,rect,axes,depth=0):
        xy=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]
        if depth==len(axes):
            kids=[add(root,p,sinks=q) for p,q in chunks(ids)]
            return add(root,xy,kids)
        axis=axes[depth];split=xy[axis];left=[q for q in ids if inv['cells'][q]['xy'][axis]<split];leftset=set(left);right=[q for q in ids if q not in leftset]
        kids=[]
        for side,qq in enumerate([left,right]):
            if not qq:continue
            box=list(rect);box[axis+2 if side==0 else axis]=split
            kids.append(build(root,qq,box,axes,depth+1))
        return add(root,xy,kids)
    for root,ids in groups.items():
        if not ids:continue
        if root not in taps:
            # Retain the separately owned forwarded clock's geometry/load tree.
            other,rr=topology(inv,{root:ids});offset=len(nodes)
            for n in other:
                n['name']=f'ot_flat_clk_{len(nodes)}';n['children']=[j+offset for j in n['children']];nodes.append(n)
            roots[root]=rr[root]+offset
            continue
        x,y=taps[root];xi=xs.index(x);yi=ys.index(y)
        rect=[die[0] if xi==0 else (xs[xi-1]+x)/2,die[1] if yi==0 else (ys[yi-1]+y)/2,
              die[2] if xi+1==len(xs) else (x+xs[xi+1])/2,die[3] if yi+1==len(ys) else (y+ys[yi+1])/2]
        dimensions=[rect[2]-rect[0],rect[3]-rect[1]];axes=[]
        while max(dimensions)>50:
            axis=max((0,1),key=lambda a:dimensions[a]);axes.append(axis);dimensions[axis]/=2
        r=build(root,ids,rect,axes);roots[root]=r
    return nodes,roots


def model(inv,nodes,roots,libdir,input_slew_ps=80.):
    if not math.isfinite(input_slew_ps) or input_slew_ps<0:raise ValueError('invalid root input slew')
    result={};masters={v['master'] for v in inv['cells'].values() if v['kind']=='S'}
    for corner in ('TT','FF'):
        libraries=LIB.lib_cells(corner,libdir,sorted({n['master'] for n in nodes}))
        text=(Path(libdir)/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib').read_text();caps={}
        for master in masters:
            start=text.index('cell ('+master+')');end=text.find('\n  cell (',start+10);block=text[start:end if end>0 else None];pin=block.index('pin (CLK)')
            caps[master]=float(re.search(r'\b(?:rise_)?capacitance\s*:\s*([0-9.eE+-]+)',block[pin:])[1])
        arrivals={};perroot={};maxslew=0;depths={};edges=[];cell_delays={};net_delays={};owners={}
        for root,entry in roots.items():
            todo=[(entry,0.,input_slew_ps,0)]
            while todo:
                index,arrival,slew,depth=todo.pop();n=nodes[index];lib=libraries[n['master']]
                targets=[(str(k),nodes[k]['xy'],libraries[nodes[k]['master']]['cap'],k) for k in n['children']]+[(q,inv['cells'][q]['xy'],caps[inv['cells'][q]['master']],None) for q in n['sinks']]
                wire=RC._mst_length([n['xy']]+[t[1] for t in targets]);load=wire*C+sum(t[2] for t in targets)
                delay=LIB._bilin(lib['delay'],slew,load);transition=LIB._bilin(lib['trans'],slew,load);cell_delays[str(index)]=delay
                for name,xy,cap,kid in targets:
                    distance=sum(abs(a-b) for a,b in zip(n['xy'],xy));elmore=distance*R*(distance*C/2+cap);a=arrival+delay+elmore;tr=math.hypot(transition,2.2*elmore)
                    maxslew=max(maxslew,tr);edges.append(distance)
                    if kid is None:arrivals[name]=a;depths[name]=depth+1;owners[name]=index;net_delays["sink:"+name]=elmore
                    else:todo.append((kid,a,tr,depth+1));net_delays["node:"+str(kid)]=elmore
            values=[arrivals[q] for n in nodes if n['root']==root for q in n['sinks']]
            perroot[root]=dict(count=len(values),min_ps=min(values),max_ps=max(values),mean_ps=sum(values)/len(values),min_stages=min(depths[q] for n in nodes if n['root']==root for q in n['sinks']),max_stages=max(depths[q] for n in nodes if n['root']==root for q in n['sinks']))
        result[corner]=dict(per_root=perroot,max_slew_ps=maxslew,max_buffer_or_sink_leg_um=max(edges),global_range_ps=max(arrivals.values())-min(arrivals.values()),sink_arrival_ps=arrivals,clock_components=dict(cell_ps=cell_delays,net_ps=net_delays,sink_owner=owners))
    return result


def related_pair_bounds(inv,nodes,groups,metrics,pairs):
    import clk_aocv as AO
    import die_sta_related as CAL
    table=AO.load(Path(__file__).with_name('clk_aocv_table_g021.json'))
    parent={kid:i for i,n in enumerate(nodes) for kid in n['children']}
    root_of={q:root for root,ids in groups.items() for q in ids}
    result={}
    for corner,m in metrics.items():
        comp=m['clock_components'];owners=comp['sink_owner'];paths={};cache={}
        for q,owner in owners.items():
            path=[owner]
            while path[-1] in parent:path.append(parent[path[-1]])
            paths[q]=path[::-1]
        categories=defaultdict(list)
        for a,b in pairs:
            ra,rb=root_of[a],root_of[b]
            category='primary' if ra.startswith('clk') and rb.startswith('clk') else 'same_forwarded' if ra==rb else 'forwarded_landing_window' if ra.startswith('clk')!=rb.startswith('clk') else 'unqualified_cross_forwarded'
            key=(owners[a],owners[b])
            if key not in cache:
                aa,bb=paths[a],paths[b];common=0
                while common<min(len(aa),len(bb)) and aa[common]==bb[common]:common+=1
                x,y=aa[common:],bb[common:]
                def side(path):
                    late=early=0.
                    for k in path:
                        factor=CAL.cell_cal_factors(corner,[nodes[k]['master']])
                        late+=comp['cell_ps'][str(k)]*factor['rise_late']
                        early+=comp['cell_ps'][str(k)]*factor['rise_early']
                    net=sum(comp['net_ps'].get('node:'+str(k),0) for k in path)
                    return late+net,early+net,dict(cell_ps=max(late,early),net_ps=net,stages={'A':len(path)})
                left,right=side(x),side(y)
                pts=[nodes[k]['xy'] for k in x+y]+[inv['cells'][q]['xy'] for q in nodes[owners[a]]['sinks']+nodes[owners[b]]['sinks']]
                distance=sum(max(p[i] for p in pts)-min(p[i] for p in pts) for i in (0,1)) if pts else 0
                cache[key]=(left,right,distance)
            left,right,distance=cache[key]
            na=comp['net_ps']['sink:'+a];nb=comp['net_ps']['sink:'+b]
            ac=dict(left[2],net_ps=left[2]['net_ps']+na);bc=dict(right[2],net_ps=right[2]['net_ps']+nb)
            # One flat CORE PDN domain: shared supply droop, but CPPR only actual
            # planned common tree cells. No mesh/common-node fiction.
            pessimism=max(AO.branch_pessimism(table,corner,ac,bc,distance,True,check) for check in ('setup','hold'))
            bound=max(left[0]+na-right[1]-nb,right[0]+nb-left[1]-na)+pessimism
            categories[category].append((bound,a,b))
        result[corner]={cat:dict(pairs=len(values),max_ps=max(v[0] for v in values),over80=sum(v[0]>80 for v in values),worst=sorted(values,reverse=True)[:5]) for cat,values in categories.items()}
    return result


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('geometry',type=Path);a.add_argument('--libdir',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--native-sdc',type=Path);a.add_argument('--input-slew-ps',type=float,default=80.);a.add_argument('--endpoint-packet',type=Path);a.add_argument('--module');a.add_argument('--fixed-h',action='store_true');a.add_argument('--max-leg',type=float,default=150);a.add_argument('--leaf-cap',type=int,default=32);args=a.parse_args()
    if args.out.exists():raise FileExistsError('preserve previous verdict; use new output')
    inv=inventory(args.geometry)
    if args.endpoint_packet:
        if not args.module:raise ValueError("--module required for exact endpoint overlay")
        overlay_endpoints(inv,args.endpoint_packet,args.module)
    groups=assign(inv);nodes,roots=topology_h(inv,groups) if args.fixed_h else topology(inv,groups,args.max_leg,args.leaf_cap);metrics=model(inv,nodes,roots,args.libdir,args.input_slew_ps);pairs=structural_pairs(args.geometry,inv)
    for corner,m in metrics.items():
        arrivals=m["sink_arrival_ps"];worst=sorted(((abs(arrivals[a]-arrivals[b]),a,b) for a,b in pairs),reverse=True)
        m["structural_pair_raw"]=dict(pairs=len(pairs),max_ps=worst[0][0] if worst else 0,over80=sum(v[0]>80 for v in worst),worst=worst[:5],basis="actual data/reset connectivity; asynchronous reset conservatively included; OCV not yet charged")
    report=dict(schema='opentallas.flat_clock_candidate.v1',native_sdc_sha256=hashlib.sha256(args.native_sdc.read_bytes()).hexdigest() if args.native_sdc else None,wire_rc=dict(r_kohm_um=R,c_ff_um=C,basis='native calibrated set_wire_rc -clock'),input_slew_ps=args.input_slew_ps,geometry_path=str(args.geometry.resolve()),structural_pairs=pairs,related_pair_model=related_pair_bounds(inv,nodes,groups,metrics,pairs),inventory=inv,groups=groups,nodes=nodes,root_nodes=roots,model=metrics,verdict='UNQUALIFIED_MODEL_ONLY',build_allowed=False,data_cycles_added=0,notes=['supplied native geometry; endpoint/placement completeness requires owner review','no row/legal-site qualification','no actual related-pair OCV/CPPR signoff yet','no measured CTS/STA delays consumed'])
    with gzip.open(args.out,'wt') as f:json.dump(report,f)
    print(json.dumps(dict(sinks=sum(len(q) for q in groups.values()),roots=len(roots),drivers=len(nodes),primary_max=max(len(q) for n,q in groups.items() if n.startswith('clk')),corners={c:{k:v for k,v in m.items() if k not in ('sink_arrival_ps','clock_components')} for c,m in metrics.items()})))

if __name__=='__main__':main()
