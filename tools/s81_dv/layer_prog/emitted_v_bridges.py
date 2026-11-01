"""Expose actual middle-V primitive inputs; no transparent-bridge assumption."""
import hashlib,json,re
from pathlib import Path
from layer_prog.emitted_leaf_routes import Wiring
from layer_prog.emitted_norm_source import EmittedNormSource,_params


def compose(nx,bridges):
    """Walk actual full V paths, retaining each primitive latency as a term.

    Primitive direction rules below are actual source interfaces, not an
    assumption that every bridge is a zero-cycle transparent wire.
    """
    if nx['source_top_sha256']!=bridges['source_top_sha256']:raise ValueError('V path sources differ')
    links={(r['receiver'],r['input']):r for r in bridges['inputs']if r['status']=='PASS_CURRENT_V_BOUNDARY'}
    links.update({(r['receiver'],r['input']):r for r in bridges['gunit_local_links']})
    slices={r['receiver']:r['slice']for r in nx['ring']}
    result=[]
    for receive in nx['ring']:
        if receive['input']!='vi':continue
        if 'source'not in receive or 'edges'not in receive:raise ValueError('current full V receive path absent')
        at,output=receive['source'],receive['output'];edges=receive['edges'];path=[];seen=set()
        while at not in slices:
            if(at,output)in seen:raise ValueError('cyclic actual middle-V source')
            seen.add((at,output))
            if at.startswith('u_gunit.u_l'):
                if at=='u_gunit.u_l3':inp={'vo_s':'rn_i','rn_o':'vi_s'}.get(output)
                elif at=='u_gunit.u_l5':inp={'vo_n':'rs_i','rs_o':'vi_n'}.get(output)
                else:inp={'rn_o':'rs_i','rs_o':'rn_i'}.get(output)
            else:inp={'vo_s':'vi_n','vo_n':'vi_s'}.get(output)
            if inp is None:raise ValueError('unmodeled current primitive V interface')
            link=links.get((at,inp))
            if link is None:raise ValueError('actual middle V wire absent: '+at+'.'+inp)
            wire=link.get('edges',link.get('wrapper_edges'))
            path.append(dict(primitive=at,input=inp,output=output,local_forward_edges=None,
                             upstream_source=link['source'],upstream_output=link['output'],upstream_wire_edges=wire))
            edges+=wire;at,output=link['source'],link['output']
        peer=slices[at];dst=receive['slice']
        sid=lambda s:2*int(s[4])+(s[-1]=='N')
        if sid(peer)!=(sid(dst)^1)or output!='vo':raise ValueError('actual full V path reaches wrong slice/port')
        result.append(dict(source_slice=peer,destination_slice=dst,boundary_and_wrapper_edges=edges,
                           primitive_terms=list(reversed(path)),source_local_forward_edges=None,physical_phases_qualified=False))
    if len(result)!=16:raise ValueError('all16 full V paths required')
    return result


def collect(inventory,latency,nx):
    die=EmittedNormSource(inventory);top=Path(die.source_record['source_top']);text=top.read_text()
    if nx['source_top_sha256']!=die.die_sha:raise ValueError('current NX source differs')
    names=json.loads((top.parent.parent/'bind_names.json').read_text());inverse={}
    for physical,canonical in names.items():inverse.setdefault(canonical,[]).append(physical)
    buses={(r['dst'],r['bus_in']):r for r in json.loads(Path(latency).read_text())['buses']}
    candidates=set()
    for r in nx['ring']:
        if r['input']=='vi'and r['status']=='UNRESOLVED_NX':
            m=re.search(r"\('([^']+)', 'vo_[sn]'\)",r['reason'])
            if m:candidates.add(m[1])
    out=[];gunit_units=[]
    candidates.update('u_gunit.u_l'+str(k)for k in range(6))
    for canonical in sorted(candidates):
        hits=inverse.get(canonical,[])
        if len(hits)!=1:raise ValueError('one actual bridge identity required: '+canonical)
        part,instance=hits[0].split('.',1)
        h=re.search(r'^\s*(\w+)(?:[ \t]+#\(([^\n]*?)\))?[ \t]+'+re.escape(part)+r'\s*\(',text,re.M)
        if not h:raise ValueError('actual bridge partition absent')
        file=top.parent/(h[1]+'.sv');body=file.read_text();w=Wiring(body)
        unit=re.search(r'^\s*(\w+)(?:[ \t]+#\(([^\n]*?)\))?[ \t]+'+re.escape(instance)+r'\s*\((.*?)^\s*\);',body,re.M|re.S)
        if not unit:raise ValueError('actual bridge atomic source absent')
        ports=_params(unit[3])
        if canonical.startswith('u_gunit.u_l'):
            gunit_units.append(dict(canonical=canonical,master=unit[1],ports=ports,wiring=w,part=part))
        for port in ('vi_s','vi_n'):
            if port not in ports:continue
            r=dict(receiver=canonical,receiver_master=unit[1],receiver_parameters=_params(unit[2]or''),input=port,
                   receiver_part=part,wrapper_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
            try:
                bits=w.bits(ports[port]);sources=set();ages=set();lanes=set()
                if len(bits)!=276:raise ValueError('V bridge fragment width differs')
                for i,bit in enumerate(bits):
                    q,j,extra=w.trace(bit,set(w.inputs));expr,width=w.inputs[q];ext=w.bits(expr)[j]
                    if ext[0]in w.landings:ext=w.bits(w.landings[ext[0]])[ext[1]]
                    bus=buses[(part,ext[0])];src=bus['source_bits'][j]
                    if width!=bus['width']or ext[1]!=j or len(src)!=4 or src[0]!='leaf'or src[3]!=i:
                        raise ValueError('actual V bridge source/bit order differs: '+str(src))
                    sources.add((src[1],src[2]));ages.add(bus['bound_stages']+extra);lanes.add(bus['lane'])
                if len(sources)!=1 or len(ages)!=1 or len(lanes)!=1:raise ValueError('V bridge word source/age incoherent')
                source,output=sources.pop();r.update(status='PASS_CURRENT_V_BOUNDARY',source=source,output=output,edges=ages.pop(),lane=lanes.pop(),bits=276)
            except (ValueError,KeyError)as exc:r.update(status='UNRESOLVED_CURRENT_V_BOUNDARY',reason=str(exc))
            out.append(r)
    local=[];drivers={}
    for u in gunit_units:
        for port in ('rn_o','rs_o','vo_n','vo_s'):
            if port not in u['ports']:continue
            for i,bit in enumerate(u['wiring'].bits(u['ports'][port])):
                if bit in drivers:raise ValueError('ambiguous actual Gunit rung driver')
                drivers[bit]=(u['canonical'],port,i)
    terminals={name for name,index in drivers}
    for u in gunit_units:
        for port in ('rn_i','rs_i'):
            if port not in u['ports']:continue
            sources=set();ages=set();bits=u['wiring'].bits(u['ports'][port])
            if len(bits)!=276:raise ValueError('actual Gunit rung width differs')
            for i,bit in enumerate(bits):
                name,index,age=u['wiring'].trace(bit,terminals);source,sport,j=drivers[(name,index)]
                if i!=j:raise ValueError('actual Gunit rung bit order differs')
                sources.add((source,sport));ages.add(age)
            if len(sources)!=1 or len(ages)!=1:raise ValueError('actual Gunit rung word is incoherent')
            source,sport=sources.pop();local.append(dict(source=source,output=sport,receiver=u['canonical'],input=port,bits=276,wrapper_edges=ages.pop()))
    return dict(schema='opentallas.s81.current_middle_V_bridge_inputs.v1',source_top_sha256=die.die_sha,
        status='CURRENT_V_BRIDGE_INPUTS_EXTRACTED',inputs=out,gunit_local_links=local,local_bridge_forward_edges=None,
        transparent_bridge_assumed=False,global_XQ_BF16_calendar_qualified=False,full_token=False)
