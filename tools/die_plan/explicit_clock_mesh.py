"""Import a declared segmented clock mesh as real fixed metal and VIA89s.

The continuous mesh joins the outputs of all declared fine/band drivers.  It
replaces their diagnostic leaf stubs; it never invents a clock buffer or changes
an existing cell's master/site.  Output ports are the mesh/local-tree boundary,
not a claim that the local partition clock trees have been built or timed.
"""
from collections import defaultdict, deque
import math


def point(layer, x, y):
    return layer, round(float(x), 4), round(float(y), 4)


def conductor_graph(mesh):
    """Split every strap at crossings/attachments and retain each cycle edge.

    A VIA89 is represented once by the edge between its M8 and M9 nodes.
    The encoder can then emit every physical conductor, including mesh cycles.
    """
    hs = [(float(s['y']), float(s['x0']), float(s['x1'])) for s in mesh['M8']]
    vs = [(float(s['x']), float(s['y0']), float(s['y1'])) for s in mesh['M9']]
    if not hs or not vs:
        raise ValueError('explicit mesh requires M8 and M9 segments')
    hp = [{x0, x1} for y, x0, x1 in hs]
    vp = [{y0, y1} for x, y0, y1 in vs]
    hy, vx = defaultdict(list), defaultdict(list)
    for i, (y, x0, x1) in enumerate(hs):
        if x1 <= x0: raise ValueError('nonpositive mesh M8 segment')
        hy[round(y, 4)].append(i)
    for j, (x, y0, y1) in enumerate(vs):
        if y1 <= y0: raise ValueError('nonpositive mesh M9 segment')
        vx[round(x, 4)].append(j)
    geometric = set()
    for j, (x, y0, y1) in enumerate(vs):
        for i, (y, x0, x1) in enumerate(hs):
            if y0-1e-6 <= y <= y1+1e-6 and x0-1e-6 <= x <= x1+1e-6:
                hp[i].add(x); vp[j].add(y)
                geometric.add((round(x, 4), round(y, 4)))
    declared = {(round(float(v['x']), 4), round(float(v['y']), 4)) for v in mesh['vias']}
    if len(declared) != len(mesh['vias']) or declared != geometric:
        raise ValueError(f'mesh VIA89 inventory differs: {len(mesh["vias"])} records, '
                         f'{len(declared)} unique, {len(geometric)} geometric crossings')

    def attach(x, y, limit=0.):
        x, y = round(float(x), 4), round(float(y), 4)
        for i in hy.get(y, ()):
            if hs[i][1]-1e-6 <= x <= hs[i][2]+1e-6:
                hp[i].add(x); return point('M8', x, y), 0.
        for j in vx.get(x, ()):
            if vs[j][1]-1e-6 <= y <= vs[j][2]+1e-6:
                vp[j].add(y); return point('M9', x, y), 0.
        cand = []
        for i, (yy, x0, x1) in enumerate(hs):
            if x0-1e-6 <= x <= x1+1e-6 and abs(yy-y) <= limit+1e-6:
                cand.append((abs(yy-y), 'M8', i, x, yy))
        for j, (xx, y0, y1) in enumerate(vs):
            if y0-1e-6 <= y <= y1+1e-6 and abs(xx-x) <= limit+1e-6:
                cand.append((abs(xx-x), 'M9', j, xx, y))
        if not cand: raise ValueError(f'mesh attachment {(x,y)} is off every conductor (limit {limit})')
        d, layer, i, xx, yy = min(cand)
        (hp if layer == 'M8' else vp)[i].add(xx if layer == 'M8' else yy)
        return point(layer, xx, yy), d
    drivers = []
    for d in mesh['drivers']:
        at, dist = attach(*d['xy'])
        drivers.append(dict(d, anchor=list(at), jog_um=dist))
    taps = []
    tap_jogs = []
    for t in mesh.get('taps', []):
        at, dist = attach(*t['xy'], limit=float(mesh.get('tap_jog_um', 0.)))
        port_at = at
        if dist > 1e-6:
            layer = 'M9' if at[0] == 'M8' else 'M8'
            joint = point(layer, at[1], at[2])
            port_at = point(layer, *t['xy'])
            tap_jogs.extend([(at, joint), (joint, port_at)])
        taps.append(dict(t, anchor=list(at), port_node=list(port_at), jog_um=dist))
    edges = set()
    def edge(a, b):
        if a != b: edges.add(tuple(sorted((a,b))))
    for (y,x0,x1), pts in zip(hs,hp):
        p = sorted(pts)
        for a,b in zip(p,p[1:]): edge(point('M8',a,y), point('M8',b,y))
    for (x,y0,y1), pts in zip(vs,vp):
        p = sorted(pts)
        for a,b in zip(p,p[1:]): edge(point('M9',x,a), point('M9',x,b))
    for x,y in geometric: edge(point('M8',x,y), point('M9',x,y))
    for a,b in tap_jogs: edge(a,b)
    graph = defaultdict(list)
    for a,b in edges: graph[a].append(b); graph[b].append(a)
    seen, todo = set(), [next(iter(graph))]
    for a in todo:
        if a in seen: continue
        seen.add(a); todo.extend(b for b in graph[a] if b not in seen)
    if len(seen) != len(graph): raise ValueError('explicit mesh has disconnected physical conductors')
    return dict(nodes=[list(n) for n in sorted(graph)], edges=[[list(a),list(b)] for a,b in sorted(edges)],
                drivers=drivers, taps=taps, tap_jog_segments=[[list(a),list(b)] for a,b in tap_jogs if a[0]==b[0]],
                strap_crossings=len(geometric),
                vias=sum(a[0]!=b[0] for a,b in edges), connected_components=1)


def attach_mesh(spec, cells, nets, ports, out):
    """Replace diagnostic tree leaf stubs with the full continuous mesh."""
    mesh = spec.get('mesh')
    if not mesh: return cells, nets, ports, out
    import die_clock_mesh as D
    ndr = mesh.get('ndr', '8w')
    if ndr not in D.NDR: raise ValueError(f'unsupported explicit mesh NDR {ndr}')
    mesh = dict(mesh)
    if 'taps' not in mesh:
        mesh['taps'] = [dict(t, xy=t['tap'], source='partition') for t in mesh.get('partition_taps', [])]
        mesh['taps'] += [dict(t, source='core_drop') for t in mesh.get('core_drops', [])]
    graph = conductor_graph(mesh)
    groups = defaultdict(list)
    for n,c in cells.items(): groups['g'+str(c['group'])].append(n)
    dg = [d['group'] for d in graph['drivers']]
    if len(set(dg)) != len(dg): raise ValueError('duplicate mesh driver group')
    if any(g not in groups for g in dg): raise ValueError('mesh driver group is absent from actual cell inventory')
    units = {u for g in dg for u in groups[g]}
    leaves = {n['drv'] for n in nets if n['loads'] and all(p.startswith('port:') for p in n['loads'])}
    if not leaves <= units:
        raise ValueError(f'mesh driver inventory omits tree leaves {sorted(leaves-units)[:5]}')
    removed, old_ports = set(), set()
    keep = []
    for n in nets:
        if n['drv'] in units:
            if any(not p.startswith('port:') for p in n['loads']):
                raise ValueError(f'mesh driver {n["drv"]} also feeds another tree stage')
            removed.add(n['name']); old_ports.update(p[5:] for p in n['loads'])
        else: keep.append(n)
    ports = [(d,p) for d,p in ports if p not in old_ports]
    out['taps'] = [t for t in out['taps'] if t['port'] not in old_ports]
    out['fixed_wires'] = [w for w in out['fixed_wires'] if w['name'] not in removed]
    for d in graph['drivers']:
        d['units'] = sorted(groups[d['group']])
        for u in d['units']:
            cells[u]['kind'] = 'node'  # explicit net, not the legacy implicit ck_mesh region
    aliases = []
    for i,t in enumerate(graph['taps']):
        name = f'msh_t_{i}'
        t['port'] = name
        aliases.append(name); ports.append(('output',name))
        layer,x,y = t['port_node']
        out['taps'].append(dict(port=name,xy=[x,y],layer=layer,part=t.get('part'),
                                pin_size_um=[D.NDR[ndr]['width']]*2,mesh_boundary=t,
                                early_ps=0.,stub_um=0.,tap='explicit_mesh_boundary'))
    if not aliases: raise ValueError('explicit mesh has no declared local-tree boundary loads')
    nm='ck_mesh_explicit'
    drivers=sorted(units)
    keep.append(dict(name=nm,drv=drivers[0],drv_units=drivers,loads=['port:'+p for p in aliases],
                     level=99,port_aliases=aliases,explicit_mesh=True))
    segs = [('M8',s['x0'],s['y'],s['x1'],s['y']) for s in mesh['M8']]
    segs += [('M9',s['x'],s['y0'],s['x'],s['y1']) for s in mesh['M9']]
    segs += [(a[0],a[1],a[2],b[1],b[2]) for a,b in graph['tap_jog_segments']]
    w=dict(name=nm,drv=drivers[0],drv_units=drivers,loads=['port:'+p for p in aliases],
           explicit_mesh=True,ndr=ndr,segs=segs,stacks=[],branches=[],horiz=True,
           trunk_tap=list(segs[0][1:3]),mesh_graph=graph,
           wire_um=round(sum(abs(s[3]-s[1])+abs(s[4]-s[2]) for s in segs),4))
    out['fixed_wires'].append(w)
    out['explicit_mesh']=graph
    out['meta']['explicit_mesh']=dict(ndr=ndr,drivers=len(dg),driver_units=len(units),
         local_tree_boundaries=len(aliases),vias=graph['vias'],connected_components=1,
         scope='fixed mesh through local-tree boundary only; downstream local trees not imported or timed')
    return cells,keep,ports,out


def routed_mesh_tcl(L, w, cells, ports, buf, rec):
    """One regular FIXED dbWire: all mesh segments, one VIA89 per crossing.

    Every physical edge is emitted, including cycle-closing chords. Chords start
    at an existing junction and end at the already declared physical coordinate;
    no duplicate crossing via is introduced. Extraction must still qualify the
    resulting circuit before this is a signed mesh.
    """
    import clock_routed as C
    g=w['mesh_graph']
    from die_clock_mesh import NDR
    nd = NDR[w.get('ndr', '8w')]
    L.extend(['set em_saved_ndr $ot_ndr',
              f'if {{[$blk findNonDefaultRule ot_explicit_mesh_ndr] == "NULL"}} {{ create_ndr -name ot_explicit_mesh_ndr -width {{M8 {nd["width"]} M9 {nd["width"]}}} -spacing {{M8 {nd["space"]} M9 {nd["space"]}}} }}',
              'set ot_ndr [$blk findNonDefaultRule ot_explicit_mesh_ndr]'])
    graph=defaultdict(list)
    for a,b in g['edges']:
        a,b=tuple(a),tuple(b);graph[a].append(b);graph[b].append(a)
    start=min(graph); seen={start}; todo=deque([start]); emitted=set()
    jid={start:'emj0'}
    L.extend([f'set w [rnet {w["name"]}]','$e begin $w',
              f'$e newPath [LY {start[0]}] FIXED [RL {start[0]}]',
              f'set emj0 [$e addPoint {C.q(start[1])} {C.q(start[2])}]'])
    nv=0
    while todo:
        a=todo.popleft()
        for b in sorted(graph[a]):
            e=tuple(sorted((a,b)))
            if e in emitted: continue
            emitted.add(e)
            L.append(f'$e newPath ${jid[a]} FIXED [RL {a[0]}]')
            fresh=b not in seen
            target=f'emj{len(jid)}' if fresh else f'emch{len(emitted)}'
            if a[0]!=b[0]:
                if a[1:]!=b[1:]: raise ValueError('mesh via has noncoincident ends')
                L.append(f'set {target} [$e addTechVia [V {{VIA89}}]]');nv+=1
            else:
                if a[1]!=b[1] and a[2]!=b[2]: raise ValueError('non-Manhattan mesh edge')
                L.append(f'set {target} [$e addPoint {C.q(b[1])} {C.q(b[2])}]')
            if fresh:
                seen.add(b);jid[b]=target;todo.append(b)
    if len(seen)!=len(graph) or nv!=g['vias']: raise ValueError('mesh encoder omitted conductor/via')
    for d in g['drivers']:
        at=tuple(d['anchor'])
        for u in d['units']:
            px,py=C.pin_point(cells,u,'Y',cells[u].get('lib',buf))
            pts=C.stair(at[0],at[1],at[2],px,py)
            L.append(f'$e newPath ${jid[at]} FIXED [RL {at[0]}]')
            begin=len(L)
            C._emit_steps(L,pts,split_down=True)
            # The caller may substitute a wide top-tree via array globally.
            # Mesh pin access is under the mesh's own NDR and keeps its tech via.
            for j in range(begin,len(L)):
                L[j]=L[j].replace('$e addTechVia [V VIA89]','$e addTechVia [V {VIA89}]')
            for a,b in zip(pts,pts[1:]):
                if a[0]==b[0] and a[0] in ('M8','M9') and a[1:]!=b[1:]:
                    rec.setdefault('extra_top',[]).append((w['name'],a[0],a[1],a[2],b[1],b[2]))
            L.append(f'$e addITerm [IT {u} Y]')
            rec['pin_stairs']=rec.get('pin_stairs',0)+1
    for t in g['taps']:
        at=tuple(t['port_node']);pn=t['port']
        L.extend([f'$e newPath ${jid[at]} FIXED [RL {at[0]}]',
                  f'$e addPoint {C.q(at[1])} {C.q(at[2])}',f'$e addBTerm [BT {pn}]'])
        rec['port_joins']=rec.get('port_joins',0)+1
    L.extend(['$e end', 'set ot_ndr $em_saved_ndr'])
    rec['nets']=rec.get('nets',0)+1
    rec.setdefault('explicit_mesh',[]).append(dict(name=w['name'],nodes=len(graph),edges=len(emitted),vias=nv,
                       driver_units=sum(len(d['units']) for d in g['drivers']),taps=len(g['taps'])))


def access_paths(w,cells,buf):
    import clock_routed as C
    return [C.stair(d['anchor'][0],d['anchor'][1],d['anchor'][2],
                    *C.pin_point(cells,u,'Y',cells[u].get('lib',buf)))
            for d in w['mesh_graph']['drivers'] for u in d['units']]


def access_shapes(w,cells,buf):
    """Actual driver access, included in the existing cross-net census."""
    import clock_routed as C
    vr=C.via_rects();out=[]
    for pts in access_paths(w,cells,buf):
        for (l0,x0,y0),(l1,x1,y1) in zip(pts,pts[1:]):
            if l0!=l1:
                for lay,(hx,hy) in vr[C.via(l0,l1)].items():
                    out.append((w['name'],lay,x0-hx,y0-hy,x0+hx,y0+hy))
            elif (x0,y0)!=(x1,y1) and l0 not in ('M8','M9'):
                h=C.WIDTH[l0]/2
                out.append((w['name'],l0,min(x0,x1)-h,min(y0,y1)-h,max(x0,x1)+h,max(y0,y1)+h))
    return out


def mesh_spef_section(w,cells,buf,layer_rc,via_kohm):
    """Native ladder for every mesh conductor and all actual output drivers.

    The geometry graph is exact; pin-stack resistance uses the same lumped
    stack model as the legacy native SPEF. Extracted RC remains the timing basis.
    """
    from die_clock_mesh import NDR
    import clock_routed as C
    nd=NDR[w['ndr']];g=w['mesh_graph'];nm=w['name']
    ids={tuple(p):f'{nm}:{i+1}' for i,p in enumerate(g['nodes'])}
    caps=defaultdict(float);res=[];conn=[];seq=[len(ids)]
    def nid():
        seq[0]+=1;return f'{nm}:{seq[0]}'
    for aa,bb in g['edges']:
        a,b=tuple(aa),tuple(bb);pa,pb=ids[a],ids[b]
        if a[0]!=b[0]:
            res.append((pa,pb,max(1e-9,via_kohm['M9']-via_kohm['M8'])))
            continue
        length=abs(b[1]-a[1])+abs(b[2]-a[2]);rr,cc=layer_rc[a[0]]
        count=max(1,math.ceil(length/54.));prev=pa
        for j in range(1,count+1):
            cur=pb if j==count else nid()
            res.append((prev,cur,rr*nd['rf']*length/count))
            caps[prev]+=cc*nd['cf']*length/count/2;caps[cur]+=cc*nd['cf']*length/count/2
            prev=cur
    for d in g['drivers']:
        at=tuple(d['anchor'])
        for u in d['units']:
            pin=u+':Y';conn.append('*I '+pin+' O')
            px,py=C.pin_point(cells,u,'Y',cells[u].get('lib',buf))
            rr,cc=layer_rc[at[0]]
            distance=abs(px-at[1])+abs(py-at[2])
            res.append((pin,ids[at],via_kohm[at[0]]+rr*nd['rf']*distance))
            caps[ids[at]]+=cc*nd['cf']*distance
    for t in g['taps']:
        pin=t['port'];conn.append('*P '+pin+' O');res.append((ids[tuple(t['port_node'])],pin,1e-9))
    L=[f'*D_NET {nm} {sum(caps.values()):.6f}','*CONN']+conn+['*CAP']
    L += [f'{i} {n} {c:.6f}' for i,(n,c) in enumerate(sorted(caps.items()),1)]
    L += ['*RES']+[f'{i} {a} {b} {r:.9f}' for i,(a,b,r) in enumerate(res,1)]+['*END','']
    return '\n'.join(L)


def native_spef(wires,cells,buf,nd,layer_rc,via_kohm):
    """Keep legacy nets unchanged, merge width-specific V2 pieces by net.

    Every tied output pin is retained. As in the legacy native basis, pin stacks
    are lumped; this helper is a diagnostic RC model, not extracted sign-off.
    """
    import die_clock_128 as C128
    from die_clock_mesh import NDR
    header=C128.spef([],cells,buf,nd,layer_rc,via_kohm)
    sections=[]
    for w in wires:
        if w.get('explicit_mesh'):
            sections.append(mesh_spef_section(w,cells,buf,layer_rc,via_kohm));continue
        pieces=w.get('pieces')
        if not pieces:
            text=C128.spef([w],cells,buf,nd,layer_rc,via_kohm)
            sections.append('*D_NET '+text.split('*D_NET ',1)[1]);continue
        nm=w['name'];caps=defaultdict(float);res=[];conns={};next_id=[0]
        for p in pieces:
            text=C128.spef([p],cells,buf,NDR[p['ndr']],layer_rc,via_kohm)
            body=text.split('*D_NET ',1)[1].splitlines()[1:];mode='';mapping={}
            def remap(s):
                if s.startswith(nm+':') and s[len(nm)+1:].isdigit():
                    if s not in mapping:
                        next_id[0]+=1;mapping[s]=f'{nm}:{next_id[0]}'
                    return mapping[s]
                return s
            for line in body:
                a=line.split()
                if not a:continue
                if a[0] in ('*CONN','*CAP','*RES','*END'):mode=a[0];continue
                if mode=='*CONN':conns[a[1]]=line
                elif mode=='*CAP':caps[remap(a[1])]+=float(a[2])
                elif mode=='*RES':res.append((remap(a[1]),remap(a[2]),float(a[3])))
            # C128's legacy net ladder names one driver pin; preserve parallel
            # output terminals via the existing lumped native pin-stack model.
            for u in p.get('drv_units',[]):
                pin=u+':Y'
                if pin not in conns:
                    conns[pin]='*I '+pin+' O'
                    res.append((pin,p['drv']+':Y',2*via_kohm['M8']))
        sec=[f'*D_NET {nm} {sum(caps.values()):.6f}','*CONN']+[conns[k] for k in sorted(conns)]+['*CAP']
        sec += [f'{i} {n} {c:.6f}' for i,(n,c) in enumerate(sorted(caps.items()),1)]
        sec += ['*RES']+[f'{i} {a} {b} {r:.9f}' for i,(a,b,r) in enumerate(res,1)]+['*END','']
        sections.append('\n'.join(sec))
    return header+'\n'.join(sections)+'\n'
