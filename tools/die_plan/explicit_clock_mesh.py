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
        access=t.get('terminal_access_xy',t['xy'])
        if len(access)!=2:raise ValueError('terminal_access_xy must contain x and y')
        access=tuple(round(float(v),4) for v in access)
        actual=tuple(round(float(v),4) for v in t['xy'])
        if access!=actual:
            if t.get('terminal_layer') not in ('M4','M5','M6','M7'):
                raise ValueError('offset terminal access requires a declared lower-metal terminal')
            if access[0]!=actual[0] and access[1]!=actual[1]:
                raise ValueError('terminal access escape must be Manhattan')
            escape=abs(access[0]-actual[0])+abs(access[1]-actual[1])
            if escape>float(t.get('terminal_access_limit_um',2.5))+1e-6:
                raise ValueError('terminal access escape exceeds its declared local reach')
        at, dist = attach(*access, limit=float(mesh.get('tap_jog_um', 0.)))
        port_at = at
        if dist > 1e-6:
            layer = 'M9' if at[0] == 'M8' else 'M8'
            joint = point(layer, at[1], at[2])
            port_at = point(layer, *access)
            tap_jogs.extend([(at, joint), (joint, port_at)])
        terminal=t.get('terminal_layer',port_at[0])
        if terminal not in ('M4','M5','M6','M7','M8','M9'):
            raise ValueError(f'unsupported declared mesh terminal layer {terminal}')
        upper=int(port_at[0][1:]);lower=int(terminal[1:])
        step=1 if lower>upper else -1
        for k in range(upper,lower,step):
            below=point('M'+str(k+step),port_at[1],port_at[2])
            tap_jogs.append((port_at,below));port_at=below
        # Descend at the PG-free access, then follow the true terminal layer to
        # its declared pin. No upper-metal via is placed over the pin's PG rail.
        if access!=actual:
            pin_at=point(terminal,*actual)
            tap_jogs.append((port_at,pin_at));port_at=pin_at
        taps.append(dict(t, anchor=list(at), port_node=list(port_at), jog_um=dist,
                         terminal_escape_um=abs(access[0]-actual[0])+abs(access[1]-actual[1])))
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
    # Canonical minimum-area landing pads on every declared lower-terminal
    # via node. They are real metal in both encoding and cross-net census.
    import clock_routed as C
    pads=C._stack_pad()
    terminal_pads=sorted({p for a,b in tap_jogs if a[0]!=b[0] for p in (a,b) if p[0] in pads and int(p[0][1:])<8})
    graph = defaultdict(list)
    for a,b in edges: graph[a].append(b); graph[b].append(a)
    seen, todo = set(), [next(iter(graph))]
    for a in todo:
        if a in seen: continue
        seen.add(a); todo.extend(b for b in graph[a] if b not in seen)
    if len(seen) != len(graph): raise ValueError('explicit mesh has disconnected physical conductors')
    return dict(nodes=[list(n) for n in sorted(graph)], edges=[[list(a),list(b)] for a,b in sorted(edges)],
                drivers=drivers, taps=taps, terminal_pads=[list(p) for p in terminal_pads], tap_jog_segments=[[list(a),list(b)] for a,b in tap_jogs if a[0]==b[0]],
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
    # Shield machinery accepts only the reserved M8/M9 mesh. Lower-metal
    # terminal escapes are separately drawn and included in access census/RC.
    segs += [(a[0],a[1],a[2],b[1],b[2]) for a,b in graph['tap_jog_segments'] if a[0] in ('M8','M9')]
    lower_um=sum(abs(a[1]-b[1])+abs(a[2]-b[2]) for a,b in graph['tap_jog_segments'] if a[0] not in ('M8','M9'))
    w=dict(name=nm,drv=drivers[0],drv_units=drivers,loads=['port:'+p for p in aliases],
           explicit_mesh=True,ndr=ndr,segs=segs,stacks=[],branches=[],horiz=True,
           trunk_tap=list(segs[0][1:3]),mesh_graph=graph,
           wire_um=round(sum(abs(s[3]-s[1])+abs(s[4]-s[2]) for s in segs)+lower_um,4),terminal_wire_um=round(lower_um,4))
    if mesh.get('terminal_rc_tcl'):w['terminal_rc_tcl']=mesh['terminal_rc_tcl']
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
              f'$e newPath [LY {start[0]}] FIXED'+(f' [RL {start[0]}]' if start[0] in ('M8','M9') else ''),
              f'set emj0 [$e addPoint {C.q(start[1])} {C.q(start[2])}]'])
    nv=0
    while todo:
        a=todo.popleft()
        for b in sorted(graph[a]):
            e=tuple(sorted((a,b)))
            if e in emitted: continue
            emitted.add(e)
            L.append(f'$e newPath ${jid[a]} FIXED'+(f' [RL {a[0]}]' if a[0] in ('M8','M9') else ''))
            fresh=b not in seen
            target=f'emj{len(jid)}' if fresh else f'emch{len(emitted)}'
            if a[0]!=b[0]:
                if a[1:]!=b[1:]: raise ValueError('mesh via has noncoincident ends')
                L.append(f'set {target} [$e addTechVia [V {{{C.via(a[0],b[0])}}}]]');nv+=1
            else:
                if a[1]!=b[1] and a[2]!=b[2]: raise ValueError('non-Manhattan mesh edge')
                L.append(f'set {target} [$e addPoint {C.q(b[1])} {C.q(b[2])}]')
            if fresh:
                seen.add(b);jid[b]=target;todo.append(b)
    if len(seen)!=len(graph) or nv!=g['vias']: raise ValueError('mesh encoder omitted conductor/via')
    for pp in g.get('terminal_pads',[]):
        p=tuple(pp);hx,hy=C._stack_pad()[p[0]]
        L.extend([f'$e newPath ${jid[p]} FIXED',
                  f'$e addRect {-C.q(hx)} {-C.q(hy)} {C.q(hx)} {C.q(hy)}'])
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
        L.extend([f'$e newPath ${jid[at]} FIXED'+(f' [RL {at[0]}]' if at[0] in ('M8','M9') else ''),
                  f'$e addPoint {C.q(at[1])} {C.q(at[2])}',f'$e addBTerm [BT {pn}]'])
        rec['port_joins']=rec.get('port_joins',0)+1
    L.extend(['$e end', 'set ot_ndr $em_saved_ndr'])
    rec['nets']=rec.get('nets',0)+1
    rec.setdefault('explicit_mesh',[]).append(dict(name=w['name'],nodes=len(graph),edges=len(emitted),vias=nv,
                       driver_units=sum(len(d['units']) for d in g['drivers']),taps=len(g['taps'])))


def access_paths(w,cells,buf):
    import clock_routed as C
    paths=[C.stair(d['anchor'][0],d['anchor'][1],d['anchor'][2],
                    *C.pin_point(cells,u,'Y',cells[u].get('lib',buf)))
            for d in w['mesh_graph']['drivers'] for u in d['units']]
    # Actual declared terminal via stacks participate in cross-net geometry.
    paths += [[tuple(a),tuple(b)] for a,b in w['mesh_graph']['edges']
              if min(int(a[0][1:]),int(b[0][1:]))<8]
    return paths


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
    for layer,x,y in w['mesh_graph'].get('terminal_pads',[]):
        hx,hy=C._stack_pad()[layer]
        out.append((w['name'],layer,x-hx,y-hy,x+hx,y+hy))
    return out


def terminal_rc_basis(w,layer_rc,via_kohm,wire_layers,via_layers):
    """Opt-in measured lower-layer native model; parse data without Tcl eval.

    Existing top-metal coefficients stay authoritative for their legacy native
    basis. Actual extracted RC remains the timing authority for every layer.
    """
    import hashlib,re
    from pathlib import Path
    missing_wire=set(wire_layers)-set(layer_rc)
    missing_via=set(via_layers)-set(via_kohm)
    if not missing_wire and not missing_via:return layer_rc,via_kohm
    selected=w.get('terminal_rc_tcl')
    if not selected:
        raise ValueError('explicit mesh native RC missing declared layer coefficients: '
                         f'wire={sorted(missing_wire)}, cumulative_via={sorted(missing_via)}; '
                         'select mesh.terminal_rc_tcl explicitly')
    repo=Path(__file__).resolve().parents[2];relative=Path(selected)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('terminal_rc_tcl must be repository-relative')
    path=repo/relative
    if not path.is_file():raise ValueError(f'terminal_rc_tcl missing: {relative}')
    data=path.read_text();layers={};vias={}
    number=r'([-+0-9.eE]+)'
    for line in data.splitlines():
        match=re.fullmatch(r'\s*set_layer_rc -layer (M[1-9]) -resistance '+number+r' -capacitance '+number+r'\s*(?:#.*)?',line)
        if match:
            name,rr,cc=match.groups()
            if name in layers:raise ValueError(f'duplicate layer coefficient {name} in terminal_rc_tcl')
            value=(float(rr),float(cc))
            if not all(math.isfinite(v) and v>=0 for v in value):raise ValueError('invalid terminal layer RC')
            layers[name]=value
        match=re.fullmatch(r'\s*set_layer_rc -via (V[1-9]) -resistance '+number+r'\s*(?:#.*)?',line)
        if match:
            name,rr=match.groups()
            if name in vias:raise ValueError(f'duplicate via coefficient {name} in terminal_rc_tcl')
            value=float(rr)
            if not math.isfinite(value) or value<=0:raise ValueError('invalid terminal via RC')
            vias[name]=value
    cumulative={'M1':0.}
    for k in range(1,9):
        if 'M'+str(k) in cumulative and 'V'+str(k) in vias:
            cumulative['M'+str(k+1)]=cumulative['M'+str(k)]+vias['V'+str(k)]
    if missing_wire-set(layers) or missing_via-set(cumulative):
        raise ValueError('terminal_rc_tcl lacks requested wire/via layer coefficients: '
                         f'wire={sorted(missing_wire-set(layers))}, via={sorted(missing_via-set(cumulative))}')
    for name in ('M8','M9'):
        if name in via_kohm and name in cumulative and abs(via_kohm[name]-cumulative[name])>1e-9:
            raise ValueError(f'terminal_rc_tcl cumulative {name} differs from existing native via basis')
    rc=dict(layer_rc);vk=dict(via_kohm)
    rc.update({k:layers[k] for k in missing_wire});vk.update({k:cumulative[k] for k in missing_via})
    w['terminal_rc_basis']=dict(path=relative.as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               wire={k:list(rc[k]) for k in sorted(missing_wire)},
                               cumulative_via={k:vk[k] for k in sorted(missing_via)},
                               scope='measured calibrated lower-layer native diagnostic; actual RCX remains timing authority')
    return rc,vk


def mesh_spef_section(w,cells,buf,layer_rc,via_kohm):
    """Native ladder for every mesh conductor and all actual output drivers.

    The geometry graph is exact; pin-stack resistance uses the same lumped
    stack model as the legacy native SPEF. Extracted RC remains the timing basis.
    """
    from die_clock_mesh import NDR
    import clock_routed as C
    nd=NDR[w['ndr']];g=w['mesh_graph'];nm=w['name']
    wire_layers={a[0] for a,b in g['edges'] if a[0]==b[0]}
    via_layers={p[0] for a,b in g['edges'] if a[0]!=b[0] for p in (a,b)}
    layer_rc,via_kohm=terminal_rc_basis(w,layer_rc,via_kohm,wire_layers,via_layers)
    ids={tuple(p):f'{nm}:{i+1}' for i,p in enumerate(g['nodes'])}
    caps=defaultdict(float);res=[];conn=[];seq=[len(ids)]
    def nid():
        seq[0]+=1;return f'{nm}:{seq[0]}'
    for aa,bb in g['edges']:
        a,b=tuple(aa),tuple(bb);pa,pb=ids[a],ids[b]
        if a[0]!=b[0]:
            res.append((pa,pb,max(1e-9,abs(via_kohm[a[0]]-via_kohm[b[0]]))))
            continue
        length=abs(b[1]-a[1])+abs(b[2]-a[2]);rr,cc=layer_rc[a[0]]
        count=max(1,math.ceil(length/54.));prev=pa
        for j in range(1,count+1):
            cur=pb if j==count else nid()
            # Lower escape wires use their native minimum-width layer RC, not
            # the mesh's wide M8/M9 factor.
            rf,cf=(nd['rf'],nd['cf']) if a[0] in ('M8','M9') else (1.,1.)
            res.append((prev,cur,rr*rf*length/count))
            caps[prev]+=cc*cf*length/count/2;caps[cur]+=cc*cf*length/count/2
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


def mixed_shield_analysis(wires,pgr,shield):
    """Use each wire's actual metal width for shield ties and spacing.

    Per-piece PG qualification is conservative: it does not assume that another
    piece's shield connection will rescue an untied stripe.
    """
    import die_clock_128 as C
    from die_clock_mesh import NDR
    pieces=[p for w in wires for p in w.get('pieces',[w])]
    shapes=[];spaces=[];allstripes=[];unflanked=[];flanked=0
    pg=C.pg_shapes(pgr)
    for shape in pg:
        width=shape[4]-shape[3]
        spaces.append(1.0 if width>=.99975 else .5 if width>=.49975 else .04)
        shapes.append(shape)
    flank_pg=list(pgr)
    for p in pieces:
        if not p.get('explicit_mesh'):continue
        # The mesh's actual, separately tie-checked VSS shields can flank a
        # neighboring input-tree segment in the same physical PG gap.
        for shape in C.clock_shapes(C.tree_segs([p]),NDR[p['ndr']],shield):
            if shape[1]!=shield:continue
            lay,_,_,lo,hi,a0,a1=shape
            flank_pg.append((shield,lay,a0,lo,a1,hi) if lay=='M8' else (shield,lay,lo,a0,hi,a1))
    ties=dict(grid_vias=[],shield_vias=[],untied=[],shorts=[],used_grid=set(),stripes=0,
              stripes_with_grid_via=0,stripes_grid_contact=0,net=shield)
    for p in pieces:
        nd=NDR[p['ndr']];ss=C.tree_segs([p])
        cs=C.clock_shapes(ss,nd,shield)
        shapes+=cs;spaces += [nd['space']]*len(cs)
        unflanked += C.flank_census(flank_pg,ss,nd)
        flanked += sum(len(r)>7 and r[7]==C.FLANK for r in ss)
        segs=[tuple(r[:5])+(r[8],) for r in ss if r[7]==C.DRAWN]
        stripes=C.shield_stripes(segs,nd)
        t=C.shield_ties(stripes,pgr,nd['width'],net=shield)
        offset=len(allstripes)
        allstripes+=stripes
        ties['grid_vias']+=t['grid_vias'];ties['shield_vias']+=t['shield_vias']
        ties['untied'] += [offset+k for k in t['untied']]
        ties['shorts'] += [(offset+k,n) for k,n in t['shorts']]
        ties['used_grid'] |= t['used_grid']
        for key in ('stripes','stripes_with_grid_via','stripes_grid_contact'):
            ties[key]+=t.get(key,0)
    ties['grid_vias']=sorted(set(ties['grid_vias']));ties['shield_vias']=sorted(set(ties['shield_vias']))
    ix=C.MetalIndex(max(spaces or [.04]));shorts=defaultdict(int);spacing=defaultdict(int);rows=[]
    for i,s in enumerate(shapes):
        for k,_ in ix.hits(s):
            t=ix.shapes[k]
            if s[2]==t[2]=='pg':continue
            required=max(spaces[i],spaces[k])
            gp=max(t[3]-s[4],s[3]-t[4]);ga=max(t[5]-s[6],s[5]-t[6])
            if gp>=required-1e-6 or ga>=required-1e-6:continue
            what='short' if gp<1e-6 and ga<1e-6 else 'spacing'
            key='-'.join(sorted((s[2],t[2])))
            (shorts if what=='short' else spacing)[key]+=1
            if len(rows)<200:rows.append(dict(what=what,a=list(s),b=list(t),required_space_um=required))
        ix.add(s)
    census=dict(shorts=sum(shorts.values()),spacing=sum(spacing.values()),shorts_by_kind=dict(shorts),
                spacing_by_kind=dict(spacing),rows=rows,shapes=len(shapes),unflanked=unflanked,
                flank_mode_segments=flanked,rule='pair spacing=max(actual per-edge NDR classes); actual shield widths')
    return allstripes,ties,census


def mesh_reservation_shapes(mesh,shield='VSS'):
    """Reserve fixed mesh conductors before planning their input clock trees."""
    import die_clock_128 as C
    from die_clock_mesh import NDR
    nd=NDR[mesh.get('ndr','8w')]
    segs=[('M8',s['x0'],s['y'],s['x1'],s['y'],'ck_mesh_explicit','mesh') for s in mesh['M8']]
    segs += [('M9',s['x'],s['y0'],s['x'],s['y1'],'ck_mesh_explicit','mesh') for s in mesh['M9']]
    shapes=C.clock_shapes(segs,nd,shield)
    # These are actual VSS conductors; final PG tie validation remains required
    # before another clock segment may count their shielding as qualified.
    return [tuple(s[:2])+('pg',)+tuple(s[3:]) if s[1]==shield else s for s in shapes]
