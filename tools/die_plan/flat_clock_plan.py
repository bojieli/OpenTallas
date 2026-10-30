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
    cells={}; ports={}; nets=[]; outline=None;core=None
    for line in Path(path).read_text().splitlines():
        r=line.split('\t')
        if r[0]=='D':outline=list(map(float,r[1:]))
        elif r[0]=='R':core=list(map(float,r[1:]))
        elif r[0]=='C':
            rect=list(map(float,r[4:8]));cells[r[1]]=dict(id=r[1],name=r[8],master=r[3],kind=r[2],xy=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],rect=rect)
        elif r[0]=='P':ports[r[1]]=dict(name=r[2],io=r[3],signal=r[4],xy=list(map(float,r[6:8])))
        elif r[0]=='N' and r[1]=='CLOCK':nets.append(r[2:])
    macros=[c['name'] for c in cells.values() if c['kind']=='M']
    if macros:raise ValueError('flat forest does not model actual native macros: '+', '.join(macros[:5]))
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
    return dict(schema='opentallas.flat_clock_inventory.v1',geometry_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),outline=outline,core=core or outline,cells=cells,ports=ports,roots=roots)


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
            core=inv.get('core',die);points=[inv['cells'][q]['xy'] for q in ids]
            rect=[max(core[0],min(p[0] for p in points)-1.08),max(core[1],min(p[1] for p in points)-.27),
                  min(core[2],max(p[0] for p in points)+1.08),min(core[3],max(p[1] for p in points)+.27)]
            dimensions=[rect[2]-rect[0],rect[3]-rect[1]];axes=[]
            levels=max(0,math.ceil(math.log2(max(1,len(ids)/32))))
            while len(axes)<levels or max(dimensions)>50:
                axis=max((0,1),key=lambda a:dimensions[a]);axes.append(axis);dimensions[axis]/=2
            if not axes and len(chunks(ids))==1:
                xy,qq=chunks(ids)[0];tree=add(root,xy,sinks=qq)
            else:tree=build(root,ids,rect,axes)
            # Plan the physical entry driver inside the native core. The real
            # port coordinate is retained and its feed RC is modeled separately.
            xy=[min(max(ports[root][0],core[0]+.81),core[2]-.81),min(max(ports[root][1],core[1]+.135),core[3]-.135)]
            roots[root]=add(root,xy,[tree])
            continue
        x,y=taps[root];xi=xs.index(x);yi=ys.index(y)
        rect=[die[0] if xi==0 else (xs[xi-1]+x)/2,die[1] if yi==0 else (ys[yi-1]+y)/2,
              die[2] if xi+1==len(xs) else (x+xs[xi+1])/2,die[3] if yi+1==len(ys) else (y+ys[yi+1])/2]
        dimensions=[rect[2]-rect[0],rect[3]-rect[1]];axes=[]
        while max(dimensions)>50:
            axis=max((0,1),key=lambda a:dimensions[a]);axes.append(axis);dimensions[axis]/=2
        r=build(root,ids,rect,axes);roots[root]=r
    return nodes,roots


def attach_native_sdc(inv,path):
    """Existing generated-clock export fanout belongs to the input-root RC."""
    text=Path(path).read_text();byname={p['name']:p for p in inv['ports'].values()};exports=defaultdict(list)
    def actual(name):
        names=[n for n in (name,name+'[0]') if n in byname]
        if len(names)!=1:raise ValueError('native clock export endpoint missing/ambiguous: '+name)
        return names[0]
    periods={}
    for line in text.splitlines():
        if line.startswith('create_clock '):
            period=re.search(r'-period\s+([0-9.eE+-]+)',line);targets=re.search(r'\[get_ports\s+([^\]]+)\]',line)
            if period and targets:
                for name in targets[1].strip('{} ').split():periods[actual(name)]=float(period[1])
    inv['clock_periods']=periods
    envelopes={}
    for line in text.splitlines():
        if not line.startswith('set_clock_latency -source '):continue
        match=re.fullmatch(r'set_clock_latency -source -(early|late) -clock (\S+) ([0-9.eE+-]+) \[get_ports ([^\]]+)\]',line)
        if not match:
            if '[get_ports ' in line:raise ValueError('unsupported native source-clock latency form')
            continue
        case,clock,value,targets=match.groups()
        for name in targets.strip('{} ').split():
            name=actual(name);record=envelopes.setdefault(name,dict(clock=clock))
            if record['clock']!=clock or case in record:raise ValueError('ambiguous native source-clock latency')
            record[case]=float(value)
    if envelopes and (set(envelopes)!=set(periods) or any(set(v)!={'clock','early','late'} or v['early']>v['late'] for v in envelopes.values())):
        raise ValueError('incomplete native source-clock envelope')
    inv['clock_source_envelopes']=envelopes
    for line in text.splitlines():
        if not line.startswith('create_generated_clock '):continue
        fields=re.findall(r'\[get_ports\s+([^\]]+)\]',line)
        if len(fields)!=2:raise ValueError('unsupported native generated-clock source form')
        root,out=[actual(v.strip('{} ')) for v in fields]
        if byname[root]['io']!='INPUT' or byname[out]['io']!='OUTPUT':raise ValueError('generated-clock export direction')
        exports[root].append(out)
    inv['clock_exports']=dict(exports)
    return inv


def validate_topology(inv,nodes,roots,groups):
    actual={q:r for r,record in inv['roots'].items() for q in record['sinks']}
    expected={p['name'] for p in inv['ports'].values() if p['io']=='INPUT' and re.fullmatch(r'clk(?:_t[0-9]+)?',p['name'])}|{r for r in inv['roots'] if r!='clk'}
    if set(roots)!=expected or set(groups)!=expected:raise ValueError('complete native input-root inventory required')
    visited=set();seen={};planned=defaultdict(list)
    for root,entry in roots.items():
        todo=[entry]
        while todo:
            i=todo.pop()
            if not isinstance(i,int) or not 0<=i<len(nodes) or i in visited:raise ValueError('planned clock graph cycle/sharing/index')
            visited.add(i);n=nodes[i]
            if n['root']!=root:raise ValueError('planned clock node crosses declared root')
            if not n['children'] and not n['sinks']:raise ValueError('unused clock driver')
            for q in n['sinks']:
                if q not in actual or q in seen:raise ValueError('missing/aliased native clock sink')
                original=actual[q]
                if root.startswith('clk') and not original.startswith('clk'):raise ValueError('primary root stealing')
                if not root.startswith('clk') and original!=root:raise ValueError('forwarded root stealing')
                seen[q]=root;planned[root].append(q)
            todo+=n['children']
    if visited!=set(range(len(nodes))) or set(seen)!=set(actual):raise ValueError('incomplete native forest')
    if any(sorted(groups[r])!=sorted(planned[r]) for r in roots):raise ValueError('leaf ownership differs from group inventory')
    return True


def actual_relations(candidate,geometry_path=None,sdc_path=None):
    """Reparse the immutable native source; a supplied pair list grants no trust."""
    geometry=Path(geometry_path or candidate['geometry_path']);native=inventory(geometry)
    original=candidate['inventory']
    if native['geometry_sha256']!=original['geometry_sha256']:raise ValueError('native geometry hash changed')
    sdc=sdc_path or candidate.get('native_sdc_path')
    if sdc:
        if hashlib.sha256(Path(sdc).read_bytes()).hexdigest()!=candidate.get('native_sdc_sha256'):raise ValueError('native SDC hash changed')
        attach_native_sdc(native,sdc)
    for key in ('cells','ports','roots','outline','core','clock_exports','clock_periods','clock_source_envelopes'):
        if native.get(key)!=original.get(key):raise ValueError('candidate native inventory differs from source: '+key)
    pairs=structural_pairs(geometry,native)
    if 'structural_pairs' in candidate:
        supplied=[tuple(x) for x in candidate['structural_pairs']]
        if len(supplied)!=len(pairs) or set(supplied)!=set(pairs):raise ValueError('supplied structural pair inventory incomplete/stale')
    return native,pairs


def buffer_models(corner,libdir,names):
    text=gzip.open(Path(libdir)/f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz','rt').read();result={}
    for master in names:
        start=text.index('cell ('+master+')');end=text.find('\n  cell (',start+10);block=text[start:end if end>0 else None]
        if set(re.findall(r'timing_sense\s*:\s*(\w+)',block))!={'positive_unate'}:raise ValueError('only native noninverting buffer forests supported')
        result[master]={}
        for edge in ('rise','fall'):
            match=re.search(edge+r'_capacitance_range\s*\(\s*([0-9.eE+-]+)\s*,\s*([0-9.eE+-]+)\s*\)',block)
            scalar=float(re.search(edge+r'_capacitance\s*:\s*([0-9.eE+-]+)',block)[1]);lo,hi=map(float,match.groups()) if match else (scalar,scalar)
            for state,cap in [('late',hi),('early',lo)]:
                result[master][edge+'_'+state]=dict(delay=LIB._table(block,'cell_'+edge),trans=LIB._table(block,edge+'_transition'),cap=cap)
    return result


def clock_caps(inv,libdir,corner):
    text=(Path(libdir)/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib').read_text();caps={state:{} for state in ('rise_late','rise_early','fall_late','fall_early')};edges={}
    for master in {c['master'] for c in inv['cells'].values() if c['kind']=='S'}:
        start=text.index('cell ('+master+')');end=text.find('\n  cell (',start+10);block=text[start:end if end>0 else None]
        clocks=re.findall(r'clocked_on\s*:\s*"([^"]+)"',block)
        if clocks not in (['CLK'],['!CLK']):raise ValueError(f'{corner} {master}: unsupported compound clock edge')
        edges[master]='rise' if clocks==['CLK'] else 'fall';pin=block.index('pin (CLK)');pin_block=block[pin:]
        for edge in ('rise','fall'):
            match=re.search(edge+r'_capacitance_range\s*\(\s*([0-9.eE+-]+)\s*,\s*([0-9.eE+-]+)\s*\)',pin_block)
            scalar=float(re.search(edge+r'_capacitance\s*:\s*([0-9.eE+-]+)',pin_block)[1]);lo,hi=map(float,match.groups()) if match else (scalar,scalar)
            caps[edge+'_late'][master]=hi;caps[edge+'_early'][master]=lo
    return {state:{q:values[c['master']] for q,c in inv['cells'].items() if c['kind']=='S'} for state,values in caps.items()},edges


def root_feed(inv,nodes,root,index,cap,input_slew_ps):
    from core_infra_wire import rooted_rc
    ports={p['name']:p['xy'] for p in inv['ports'].values()};exports=inv.get('clock_exports',{}).get(root,[])
    points=[ports[root],nodes[index]['xy']]+[ports[p] for p in exports]
    rc=rooted_rc(points,[cap]+[0.]*len(exports),(R,C),(R,C),merge_collinear=True)
    delay=rc['target_elmore_ps'][0]
    return delay,math.hypot(input_slew_ps,2.2*delay),dict(port_xy=ports[root],driver_xy=nodes[index]['xy'],direct_um=sum(abs(a-b) for a,b in zip(points[0],points[1])),shared_root_wire_um=rc['wire_um'],clock_exports=exports,input_cap_ff=rc['total_load_ff'],wire_delay_ps=delay)


def model(inv,nodes,roots,libdir,input_slew_ps=80.):
    import die_sta_related as CAL
    if not math.isfinite(input_slew_ps) or input_slew_ps<0:raise ValueError('invalid root input slew')
    result={}
    for corner in ('TT','FF'):
        libraries=buffer_models(corner,libdir,sorted({n['master'] for n in nodes}));caps,edges_inventory=clock_caps(inv,libdir,corner)
        active={q:edges_inventory[c['master']] for q,c in inv['cells'].items() if c['kind']=='S'}
        factors={m:CAL.cell_cal_factors(corner,[m]) for m in libraries};waves={};maxslew=0;all_legs=[]
        for state in ('rise_late','rise_early','fall_late','fall_early'):
            arrivals={};cal={};outcal={};perroot={};feeds={};depths={};cell_delays={};net_delays={};owners={}
            for root,entry in roots.items():
                feed,slew,record=root_feed(inv,nodes,root,entry,libraries[nodes[entry]['master']][state]['cap'],input_slew_ps);feeds[root]=record;net_delays['node:'+str(entry)]=feed
                todo=[(entry,feed,feed,slew,0)]
                while todo:
                    index,arrival,calarr,slew,depth=todo.pop();n=nodes[index];lib=libraries[n['master']][state];factor=factors[n['master']][state]
                    targets=[(str(k),nodes[k]['xy'],libraries[nodes[k]['master']][state]['cap'],k) for k in n['children']]+[(q,inv['cells'][q]['xy'],caps[state][q],None) for q in n['sinks']]
                    wire=RC._mst_length([n['xy']]+[t[1] for t in targets]);load=wire*C+sum(t[2] for t in targets)
                    delay=LIB._bilin(lib['delay'],slew,load);transition=LIB._bilin(lib['trans'],slew,load);cell_delays[str(index)]=delay;outcal[str(index)]=calarr+delay*factor
                    for name,xy,cap,kid in targets:
                        distance=sum(abs(a-b) for a,b in zip(n['xy'],xy));elmore=distance*R*(distance*C/2+cap);a=arrival+delay+elmore;ca=calarr+delay*factor+elmore;tr=math.hypot(transition,2.2*elmore)
                        maxslew=max(maxslew,tr);all_legs.append(distance)
                        if kid is None:arrivals[name]=a;cal[name]=ca;depths[name]=depth+1;owners[name]=index;net_delays['sink:'+name]=elmore
                        else:todo.append((kid,a,ca,tr,depth+1));net_delays['node:'+str(kid)]=elmore
            waves[state]=dict(sink_arrival_ps=arrivals,calibrated_arrival_ps=cal,node_out_calibrated_ps=outcal,root_feed=feeds,depths=depths,clock_components=dict(cell_ps=cell_delays,net_ps=net_delays,sink_owner=owners))
        selected={q:waves[edge+'_late']['sink_arrival_ps'][q] for q,edge in active.items()}
        cases={case:{q:waves[edge+'_'+case]['calibrated_arrival_ps'][q] for q,edge in active.items()} for case in ('late','early')}
        perroot={}
        for root in roots:
            ids=[q for n in nodes if n['root']==root for q in n['sinks']];values=[selected[q] for q in ids];windows={case:max(table[q] for q in ids)-min(table[q] for q in ids) for case,table in cases.items()};depths=waves['rise_late']['depths']
            perroot[root]=dict(count=len(values),min_ps=min(values),max_ps=max(values),mean_ps=sum(values)/len(values),raw_window_ps=max(values)-min(values),calibrated_windows_ps=windows,window_ps=max(windows.values()),min_stages=min(depths[q] for q in ids),max_stages=max(depths[q] for q in ids))
        result[corner]=dict(per_root=perroot,root_feed={state:w['root_feed'] for state,w in waves.items()},clock_edge_inventory=edges_inventory,active_edge=active,max_slew_ps=maxslew,max_buffer_or_sink_leg_um=max(all_legs),global_range_ps=max(selected.values())-min(selected.values()),sink_arrival_ps=selected,calibrated_sink_latency_ps=cases,waveforms=waves,window_basis='same-corner consistent late/early state; actual active edge; ideal half-cycle phase excluded')
    return result


def related_pair_bounds(inv,nodes,groups,metrics,pairs):
    import clk_aocv as AO
    import die_sta_related as CAL
    table=AO.load(Path(__file__).with_name('clk_aocv_table_g021.json'));parent={kid:i for i,n in enumerate(nodes) for kid in n['children']};root_of={q:root for root,ids in groups.items() for q in ids};result={}
    for corner,m in metrics.items():
        waves=m['waveforms'];active=m['active_edge'];owners=waves['rise_late']['clock_components']['sink_owner'];paths={};cache={};categories=defaultdict(list);phases=Counter()
        for q,owner in owners.items():
            path=[owner]
            while path[-1] in parent:path.append(parent[path[-1]])
            paths[q]=path[::-1]
        for a,b in pairs:
            ra,rb=root_of[a],root_of[b];ea,eb=active[a],active[b];phases[ea+'->'+eb]+=1
            category='primary' if ra.startswith('clk') and rb.startswith('clk') else 'same_forwarded' if ra==rb else 'forwarded_landing_window' if ra.startswith('clk')!=rb.startswith('clk') else 'unqualified_cross_forwarded'
            key=(owners[a],owners[b],ea,eb)
            if key not in cache:
                aa,bb=paths[a],paths[b];common=0
                while common<min(len(aa),len(bb)) and aa[common]==bb[common]:common+=1
                x,y=aa[common:],bb[common:];node='__source__' if not common else 'n'+str(aa[common-1]);ranges={}
                if common:
                    k=str(aa[common-1]);values=[]
                    for edge in ({ea,eb}):values.append(abs(waves[edge+'_late']['node_out_calibrated_ps'][k]-waves[edge+'_early']['node_out_calibrated_ps'][k]))
                    ranges[node]=min(values)
                def side(path,edge):
                    cells=[];nets=[]
                    for case in ('late','early'):
                        state=edge+'_'+case;comp=waves[state]['clock_components'];cell=sum(comp['cell_ps'][str(k)]*CAL.cell_cal_factors(corner,[nodes[k]['master']])[state] for k in path);net=sum(comp['net_ps'].get('node:'+str(k),0) for k in path);cells.append(cell);nets.append(net)
                    return dict(cell_ps=max(cells),net_ps=max(nets),stages={'A':len(path)})
                left,right=side(x,ea),side(y,eb);pts=[nodes[k]['xy'] for k in x+y]+[inv['cells'][q]['xy'] for q in nodes[owners[a]]['sinks']+nodes[owners[b]]['sinks']];distance=sum(max(p[i] for p in pts)-min(p[i] for p in pts) for i in (0,1));cache[key]=(left,right,distance,node,ranges)
            left,right,distance,node,ranges=cache[key]
            def tap(q,edge):
                v=[waves[edge+'_'+case]['calibrated_arrival_ps'][q] for case in ('late','early')]
                return dict(late_ps=max(v),early_ps=min(v),cppr_node=node,port=q)
            ac=dict(left,net_ps=left['net_ps']+max(waves[ea+'_'+case]['clock_components']['net_ps']['sink:'+a] for case in ('late','early')));bc=dict(right,net_ps=right['net_ps']+max(waves[eb+'_'+case]['clock_components']['net_ps']['sink:'+b] for case in ('late','early')))
            ocv=lambda _a,_b,check:AO.branch_pessimism(table,corner,ac,bc,distance,True,check)
            lo,hi,_,_=CAL.ca_pair_interval(tap(a,ea),tap(b,eb),a,b,cppr_range=ranges,ocv=ocv,edge='rise')
            categories[category].append((max(abs(lo),abs(hi)),a,b))
        result[corner]={cat:dict(pairs=len(values),max_ps=max(v[0] for v in values),over80=sum(v[0]>80 for v in values),worst=sorted(values,reverse=True)[:5]) for cat,values in categories.items()}
        result[corner]['edge_phase_info']=dict(pairs=dict(phases),opposite_edge_ideal_phase_ps=CAL.PERIOD_PS/2,basis='active-edge insertion normalized; ideal phase retained by native library/SDC, excluded from clock damage')
    return result


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('geometry',type=Path);a.add_argument('--libdir',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--native-sdc',type=Path);a.add_argument('--input-slew-ps',type=float,default=80.);a.add_argument('--endpoint-packet',type=Path);a.add_argument('--module');a.add_argument('--fixed-h',action='store_true');a.add_argument('--max-leg',type=float,default=150);a.add_argument('--leaf-cap',type=int,default=32);args=a.parse_args()
    if args.out.exists():raise FileExistsError('preserve previous verdict; use new output')
    inv=inventory(args.geometry)
    if args.native_sdc:attach_native_sdc(inv,args.native_sdc)
    if args.endpoint_packet:
        if not args.module:raise ValueError("--module required for exact endpoint overlay")
        overlay_endpoints(inv,args.endpoint_packet,args.module)
    groups=assign(inv);nodes,roots=topology_h(inv,groups) if args.fixed_h else topology(inv,groups,args.max_leg,args.leaf_cap);validate_topology(inv,nodes,roots,groups);metrics=model(inv,nodes,roots,args.libdir,args.input_slew_ps);pairs=structural_pairs(args.geometry,inv)
    for corner,m in metrics.items():
        arrivals=m["sink_arrival_ps"];worst=sorted(((abs(arrivals[a]-arrivals[b]),a,b) for a,b in pairs),reverse=True)
        m["structural_pair_raw"]=dict(pairs=len(pairs),max_ps=worst[0][0] if worst else 0,over80=sum(v[0]>80 for v in worst),worst=worst[:5],basis="actual data/reset connectivity; asynchronous reset conservatively included; OCV not yet charged")
    report=dict(schema='opentallas.flat_clock_candidate.v1',native_sdc_path=str(args.native_sdc.resolve()) if args.native_sdc else None,native_sdc_sha256=hashlib.sha256(args.native_sdc.read_bytes()).hexdigest() if args.native_sdc else None,wire_rc=dict(r_kohm_um=R,c_ff_um=C,basis='native calibrated set_wire_rc -clock'),input_slew_ps=args.input_slew_ps,geometry_path=str(args.geometry.resolve()),structural_pairs=pairs,related_pair_model=related_pair_bounds(inv,nodes,groups,metrics,pairs),inventory=inv,groups=groups,nodes=nodes,root_nodes=roots,model=metrics,verdict='UNQUALIFIED_MODEL_ONLY',build_allowed=False,data_cycles_added=0,notes=['supplied native geometry; endpoint/placement completeness requires owner review','no row/legal-site qualification','no actual related-pair OCV/CPPR signoff yet','no measured CTS/STA delays consumed'])
    with gzip.open(args.out,'wt') as f:json.dump(report,f)
    print(json.dumps(dict(sinks=sum(len(q) for q in groups.values()),roots=len(roots),drivers=len(nodes),primary_max=max(len(q) for n,q in groups.items() if n.startswith('clk')),corners={c:{k:v for k,v in m.items() if k not in ('sink_arrival_ps','clock_components','waveforms','calibrated_sink_latency_ps','active_edge')} for c,m in metrics.items()})))

if __name__=='__main__':main()
