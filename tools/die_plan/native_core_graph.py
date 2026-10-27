"""Exact core data-peer graph from native bit identities and actual producer directions.

No sibling-name, suffix, nearest-peer, or quadrant-copy inference. A native source
instance/subcore claimed by multiple physical cores is ambiguous until an actual
replica binding exists. Inputs sharing a native source are consumers, never
mistaken for a producer/consumer pair. Die buses require explicit bit bindings.
The emitted partial core_conns remains FAIL until every data endpoint is bound.
"""
import collections,json,re
from pathlib import Path


def base(n):return re.sub(r'\[\d+\]$','',n)


def build(raw,pd,connections,identity,direction,types=None,bus_bindings=None,entry_types=None):
    pd=Path(pd);rows=[];errors=[];source_users=collections.defaultdict(list);pin_cache={};cores={};cc={}
    ef=pd/'clock_entries.json';entries=json.load(open(ef)) if ef.is_file() else {}
    for tn,t in raw['partition_types'].items():
        if types and tn not in types:continue
        cc[tn]={}
        for h in t.get('hard_cores',[]):
            node=(tn,h['inst']);cores[node]=h;cc[tn][h['inst']]={}
            try:
                label,ports=connections(tn,t,h);sid=identity(tn,h,label)
                source_users[sid].append(node)
            except (ValueError,KeyError,TypeError) as e:
                errors.append(dict(type=tn,core=h['inst'],kind='native_binding',reason=str(e)));continue
            pf=h.get('pins_file')
            if not pf or not (pd/pf).is_file():errors.append(dict(type=tn,core=h['inst'],kind='pins',reason='no actual pin table'));continue
            if pf not in pin_cache:pin_cache[pf]=json.load(open(pd/pf))
            pin_names={p['name'] for p in pin_cache[pf]};physical=collections.defaultdict(list)
            for p in pin_names:physical[base(p)].append(p)
            unused=set(h.get('unused_pins',[]));ps=h.get('pin_select',{});reverse={v:k for k,v in ps.items()}
            et=(entry_types or {}).get(tn,tn)
            entry=entries.get(et,{}).get(h['inst']) or entries.get(et,{}).get(re.sub(r'__q\d+$','',h['inst']),{})
            clocks={base(p) for p in (entry.get('merged_clock_ports') or [])}
            if entry.get('port'):clocks.add(base(entry['port']))
            # Reset naming is the existing library interface contract; other
            # reset aliases need an explicit port contract, not a guessed net.
            reset_ports={'rst_n','reset_n'}
            ids={x['port'] for x in h.get('straps',[])}|set(h.get('parent_id_straps',{}))
            for group,pins in sorted(physical.items()):
                logical=reverse.get(group,group)
                if group in unused:continue
                if logical in clocks:
                    cc[tn][h['inst']][logical]=['tap:'+h['inst']+'.'+logical];continue
                if logical in reset_ports:
                    cc[tn][h['inst']][logical]=['reset:'+h['inst']+'.'+logical];continue
                if logical in ids:continue
                if logical not in ports:
                    errors.append(dict(type=tn,core=h['inst'],port=logical,kind='port_binding',reason='physical data port has no exact native/cut bit map'));continue
                vector=ports[logical];selected=[];bad=False
                for pin in pins:
                    m=re.search(r'\[(\d+)\]$',pin)
                    if not m and len(vector)!=1:
                        errors.append(dict(type=tn,core=h['inst'],port=logical,kind='width',reason=f'scalar physical pin but native width {len(vector)}'));bad=True;break
                    k=int(m[1]) if m else 0
                    if k>=len(vector):errors.append(dict(type=tn,core=h['inst'],port=logical,kind='width',reason=f'physical bit {k} absent in native width {len(vector)}'));bad=True;break
                    if vector[k] is not None:selected.append((k,tuple(vector[k])))
                if bad:continue
                if not selected:continue  # native literal constants, no routing peer invented
                io=direction(tn,h,label,logical,vector)
                if io not in ['input','output']:
                    errors.append(dict(type=tn,core=h['inst'],port=logical,kind='direction',reason='actual native driver direction is not established'));continue
                rows.append(dict(type=tn,core=h['inst'],port=logical,source_identity=sid,io=io,bits=selected))
    collisions=[];bad_nodes=set()
    for sid,users in source_users.items():
        if len(users)>1:
            tn=users[0][0] if len({n[0] for n in users})==1 else '*'
            nodes=[dict(type=n[0],core=n[1]) for n in users]
            collisions.append(dict(type=tn,source_identity=sid,physical_nodes=nodes));bad_nodes.update(users)
            errors.append(dict(type=tn,kind='replica_binding',reason='one native source instance/subcore claimed by multiple physical cores',source_identity=sid,physical_nodes=nodes))
    bybit=collections.defaultdict(list)
    for row in rows:
        if (row['type'],row['core']) in bad_nodes:continue
        for k,bit in row['bits']:bybit[(row['type'],bit)].append(dict(core=row['core'],port=row['port'],bit=k,io=row['io']))
    for binding in bus_bindings or []:
        tn,bus,io=binding['type'],binding['bus'],binding['direction']
        if tn not in cc:continue
        if io not in ['input','output']:raise ValueError('bus direction must be input to/output from partition')
        for k,bit in enumerate(binding['bits']):
            if bit is not None:bybit[(tn,tuple(bit))].append(dict(bus=bus,port=bus,bit=k,io='output' if io=='input' else 'input'))
    edges=collections.defaultdict(list);unbound=collections.defaultdict(list)
    for (tn,bit),endpoints in bybit.items():
        src=[e for e in endpoints if e['io']=='output'];dst=[e for e in endpoints if e['io']=='input']
        # Duplicate pin bits from one port count once; physically distinct
        # producers remain an error instead of being silently paired.
        src=list({(e.get('core'),e.get('bus'),e['port'],e['bit']):e for e in src}.values())
        if len(src)!=1:
            unbound[(tn,'producer_count',len(src))].append(dict(native_bit=list(bit),endpoints=endpoints));continue
        if not dst:
            unbound[(tn,'no_consumer',0)].append(dict(native_bit=list(bit),endpoints=endpoints));continue
        for target in dst:
            producer=src[0]
            if producer.get('core')==target.get('core') and producer.get('core') is not None:continue
            if 'core' in producer:
                peer='core:'+target['core'] if 'core' in target else 'bus:'+target['bus']
                cc[tn][producer['core']].setdefault(producer['port'],[]).append(peer)
            if 'core' in target:
                peer='core:'+producer['core'] if 'core' in producer else 'bus:'+producer['bus']
                cc[tn][target['core']].setdefault(target['port'],[]).append(peer)
            key=(tn,producer.get('core','bus:'+producer.get('bus','')),producer['port'],target.get('core','bus:'+target.get('bus','')),target['port'])
            edges[key].append(dict(source_bit=producer['bit'],target_bit=target['bit'],native_bit=list(bit)))
    for (tn,kind,n),bits in unbound.items():
        errors.append(dict(type=tn,kind=kind,count=len(bits),producer_count=n,reason='native data bit has no unique mapped producer/consumer; actual bus/leaf/replica binding required',sample=bits[:4]))
    for tn,c in cc.items():
        for inst,ports in c.items():
            for port in ports:ports[port]=sorted(set(ports[port]))
    edge_rows=[dict(type=k[0],source_core=k[1],source_port=k[2],target_core=k[3],target_port=k[4],bits=v) for k,v in sorted(edges.items())]
    report=dict(schema='opentallas.native_core_graph.v1',verdict='FAIL' if errors else 'PASS',errors=errors,source_alias_collisions=collisions,
                mapped_core_ports=len(rows),mapped_native_bits=len(bybit),edges=len(edge_rows),edge_bit_incidences=sum(len(e['bits']) for e in edge_rows),
                scope='Native-bit logical producer/consumer graph with transport collapsed; historical transport ages are not zero-cycle claims. Actual station/compiler latency must be priced separately. No sibling-name or replica inference. Partial graph is never routing authorization.')
    return cc,edge_rows,report
