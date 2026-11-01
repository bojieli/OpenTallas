"""Extract current NX active-bit paths without flattening the whole die.

Ring constants and intermediate non-XG producers remain explicit exclusions.
The extracted register stages are not physical phase or absolute cycle dates.
"""
import json,re
from pathlib import Path
from layer_prog.emitted_norm_source import EmittedNormSource,_params
from layer_prog.emitted_leaf_routes import Wiring

ACTIVE=[0]+list(range(4,8))+list(range(13,181))
FIELDS=(('d',160),('b',8),('h',4),('v',1))


def snake_paths(routes):
    """Compose all240 peer paths; forwarding latency stays an explicit symbol.

    Side selection is the existing xstop/rstop snake ABI, not geographic lane
    ages. Every selected edge must still be an exact emitted XG output path.
    """
    from layer_prog.norm_nx import side_ports
    direct={}
    for r in routes:
        if r['status']!='PASS_DIRECT_NX':continue
        key=(r['source_slice'],r['output'])
        if key in direct:raise ValueError('ambiguous actual NX output receiver')
        direct[key]=r
    slices=sorted({r['slice']for r in routes});paths=[]
    if len(slices)!=16:raise ValueError('all16 actual NX receivers required')
    sid=lambda sl:2*int(sl[4])+(sl[-1]=='N')
    for origin in slices:
        seen={origin}
        for side,hops in [('e',8),('w',7)]:
            at=origin;age=0;legs=[]
            for forward_count in range(hops):
                port=side_ports(sid(at))[side]
                route=direct.get((at,port))
                if route is None:raise ValueError('actual NX snake path absent: '+at+'.'+port)
                age+=route['edges'];at=route['slice']
                if at in seen:raise ValueError('actual NX snake revisits a destination')
                seen.add(at);legs=legs+[dict(lane=route['lane'],source=route['source_slice'],output=port,
                                            destination=at,input=route['input'],edges=route['edges'])]
                paths.append(dict(origin=origin,destination=at,side=side,hops_from_origin=forward_count+1,
                    boundary_edges_sum=age,prior_XG_XFIN_forward_count=forward_count,path=legs,
                    landing_offset_formula=f'{age} + {forward_count} * source_local_forward_edges'))
        if seen!=set(slices):raise ValueError('actual NX snake does not reach all16 slices')
    return paths


def collect(inventory,latency,active_bits_by_port=None):
    die=EmittedNormSource(inventory)
    bind=Path(die.source_record['source_top']).parent.parent
    names=json.loads((bind/'bind_names.json').read_text())
    raw=json.loads(Path(latency).read_text())
    if raw.get('schema')!='opentallas.die_plan.bind.v1':raise ValueError('actual bound lane record required')
    buses={(r['dst'],r['bus_in']):r for r in raw['buses']}
    ring=[];local=[];identities={}
    for sl,row in sorted(die.rows.items(),key=lambda x:x[1]['sid']):
        text=Path(row['wrapper_file']).read_text();w=Wiring(text)
        def unit(pattern):
            hits=list(re.finditer(r'^\s*('+pattern+r')(?:\s+#\((.*?)\))?\s+(\w+)\s*\((.*?)^\s*\);',text,re.M|re.S))
            if len(hits)!=1:raise ValueError('one actual '+pattern+' required')
            hit=hits[0];canonical=names[row['part']+'.'+hit[3]]
            return canonical,_params(hit[4])
        xg,g=unit('ot_s81sl_xg\\w*');xf,f=unit('ot_s81dv_xfin');xr,r=unit(re.escape(row['xr_master']))
        identities[xg]=sl
        def direct(source,sink,label):
            if len(source)!=len(sink):raise ValueError('local interface width differs: '+label)
            ages=set();term={n for n,i in source}
            for a,b in zip(source,sink):
                n,i,age=w.trace(b,term)
                if(n,i)!=a:raise ValueError('local interface order differs: '+label)
                ages.add(age)
            if len(ages)!=1:raise ValueError('local interface age differs: '+label)
            local.append(dict(slice=sl,source=label.split(' -> ')[0],destination=label.split(' -> ')[1],bits=len(source),edges=ages.pop()))
        for side,outside,inside in [('e','eo','wi'),('w','wo','ei')]:
            # XFIN eo/wo feeds XG nx_eo/nx_wo; receiving XG nx_wi/nx_ei feeds XFIN wi/ei.
            direct([b for field,width in FIELDS for b in w.bits(f[outside+'_'+field])],w.bits(g['nx_'+outside]),xf+'.'+outside+' -> '+xg+'.nx_'+outside)
            receive='wi' if side=='e' else 'ei'
            direct(w.bits(g['nx_'+receive]),[b for field,width in FIELDS for b in w.bits(f[receive+'_'+field])],xg+'.nx_'+receive+' -> '+xf+'.'+receive)
        for a,b in [('rb_v','x_rbv'),('rb_d','x_rbd')]:
            direct(w.bits(f[a]),w.bits(r[b]),xf+'.'+a+' -> '+xr+'.'+b)
        for a,b in [('x_sv','s_v'),('x_si','s_i'),('x_s','s'),('x_go','go'),('x_mode','mode'),('x_eps','eps')]:
            direct(w.bits(r[a]),w.bits(f[b]),xr+'.'+a+' -> '+xf+'.'+b)
        for port in ('ri_w','ri_e','vi'):
            selected=ACTIVE if active_bits_by_port is None else active_bits_by_port[port]
            record=dict(slice=sl,receiver=xg,input=port,active_bits=len(selected),physical_phase_qualified=False)
            try:
                bits=w.bits(g[port]);sources=set();ages=set();lanes=set();mapping=[]
                for index in selected:
                    q,j,extra=w.trace(bits[index],set(w.inputs))
                    expr,width=w.inputs[q];ext=w.bits(expr)[j]
                    if ext[0]in w.landings:ext=w.bits(w.landings[ext[0]])[ext[1]]
                    bus=buses[(row['part'],ext[0])]
                    if ext[1]!=j or width!=bus['width']:raise ValueError('boundary bit mapping differs')
                    src=bus['source_bits'][j]
                    if len(src)!=4 or src[0]!='leaf':raise ValueError('active NX bit is not an atomic output: '+str(src))
                    sources.add((src[1],src[2]));ages.add(extra+bus['bound_stages']);lanes.add(bus['lane'])
                    if src[3]!=index:raise ValueError('NX active bit order differs: '+str((index,src)))
                    mapping.append(j)
                if len(sources)!=1 or len(ages)!=1 or len(lanes)!=1:raise ValueError('NX word has incoherent source/age/lane')
                producer,output=sources.pop()
                if output not in ('ro_e','ro_w','vo'):
                    record.update(source=producer,output=output,edges=next(iter(ages)),lane=next(iter(lanes)))
                    raise ValueError('intermediate producer is not an XG ring/V output: '+str((producer,output)))
                record.update(status='PASS_DIRECT_NX',source=producer,output=output,edges=ages.pop(),lane=lanes.pop(),bus_bits=mapping)
            except (ValueError,KeyError)as exc:
                record.update(status='UNRESOLVED_NX',reason=str(exc))
            ring.append(record)
    for record in ring:
        if record['status']=='PASS_DIRECT_NX':
            if record['source']not in identities:raise ValueError('ring source not selected actual XG')
            record['source_slice']=identities[record['source']]
    paths=snake_paths(ring)
    return dict(schema='opentallas.s81.emitted_NX_transport.v1',source_top_sha256=die.die_sha,
        status='CURRENT_SOURCE_PATHS_EXTRACTED',ring=ring,local=local,
        direct_paths=sum(r['status']=='PASS_DIRECT_NX'for r in ring),snake_peer_paths=paths,
        snake_peer_paths_complete=len(paths)==240,local_forward_edges=None,
        absolute_calendar_qualified=False,physical_phase_qualified=False,full_token=False)
