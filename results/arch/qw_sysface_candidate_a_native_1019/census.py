#!/usr/bin/env python3
"""Uncapped native source-graph role census from actual Liberty semantics."""
import collections,functools,json,pathlib,re
P=pathlib.Path(__file__).resolve().parent
sem=json.loads((P/'native_semantics.json').read_text());summary={}
for which in ['original','candidate']:
    j=json.loads((P/f'mapped_{which}/netlist.json').read_text());m=next(v for k,v in j['modules'].items() if k.startswith('qfd_host'));cs=m['cells'];ls=sem[which]['all_native_types']
    sinks=collections.defaultdict(list);drivers={};transparent={};pg=[];counts=collections.Counter(c['type'] for c in cs.values())
    def role(c,p):
        if ls[c['type']]['ff']:
            return {'CLK':'clock','RESETN':'reset','SETN':'set','D':'data'}.get(p,'ff_other')
        return 'logic'
    for name,c in cs.items():
        lib=ls[c['type']]
        for pin,typ in lib['pg'].items():pg.append({'instance':name,'master':c['type'],'mterm':pin,'role':typ,'graph_binding':c['connections'].get(pin),'physical_iterm_binding':None})
        for pin,d in c['port_directions'].items():
            for b in c['connections'][pin]:
                item={'instance':name,'master':c['type'],'pin':pin,'role':role(c,pin),'capacitance':lib['pins'].get(pin,{}).get('capacitance')}
                if d=='output':drivers[b]=item
                else:sinks[b].append(item)
        if not lib['ff'] and len(lib['functions'])==1:
            op,f=next(iter(lib['functions'].items()));z=re.fullmatch(r'\s*(!?)\s*([A-Za-z_][A-Za-z0-9_]*)\s*',f)
            if z and z[2] in c['connections']:transparent[name]=(op,bool(z[1]))
    for name,p in m['ports'].items():
        for i,b in enumerate(p['bits']):
            it={'instance':'PORT','master':None,'pin':name+f'[{i}]','role':'output_port' if p['direction']=='output' else 'input_port','capacitance':None}
            if p['direction']=='input':drivers[b]=it
            else:sinks[b].append(it)
    roots=[]
    for b,dr in list(drivers.items())+[(k,{'instance':'CONSTANT','master':None,'pin':k,'role':'tie_literal'}) for k in ['0','1'] if k in sinks]:
        if dr['instance'] in transparent:continue
        q=[(b,False)];seen=set();leaves={};steps=[]
        while q:
            net,inv=q.pop()
            if (net,inv) in seen:continue
            seen.add((net,inv))
            for sk in sinks[net]:
                n=sk['instance']
                if n in transparent:
                    op,pol=transparent[n];out=cs[n]['connections'][op][0];q.append((out,inv^pol));steps.append({'instance':n,'master':cs[n]['type'],'input_pin':sk['pin'],'output_pin':op,'inverts':pol})
                else:leaves[(n,sk['pin'],inv)]={**sk,'inverted_from_root':inv}
        roots.append({'bit':b,'driver':dr,'load_count':len(leaves),'roles':dict(collections.Counter(x['role'] for x in leaves.values())),'transparent_paths':steps,'endpoints':list(leaves.values())})
    state_qn={cs[k]['connections']['QN'][0]:v for k,v in sem[which]['state_correspondence'].items()}
    input_names={b:name+f'[{i}]' for name,p in m['ports'].items() if p['direction']=='input' for i,b in enumerate(p['bits'])}
    @functools.lru_cache(None)
    def support(bit):
        if bit in state_qn:
            x=state_qn[bit];return frozenset([f'state:{x["name"]}[{x["bit"]}]'])
        if bit in input_names:return frozenset([input_names[bit]])
        if not isinstance(bit,int):return frozenset(['constant:'+bit])
        d=drivers[bit];c=cs[d['instance']]
        return frozenset().union(*(support(b) for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for b in bs))
    @functools.lru_cache(None)
    def depth(bit):
        if bit in state_qn or bit in input_names or not isinstance(bit,int):return 0
        d=drivers[bit];c=cs[d['instance']]
        return 1+max((depth(b) for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for b in bs),default=0)
    direct_electrical=[]
    for bit,d in drivers.items():
        if d['instance'] not in cs:continue
        cap=sum(float(x['capacitance']) for x in sinks[bit] if x['capacitance'] is not None)
        unknown=[x for x in sinks[bit] if x['capacitance'] is None]
        lim=ls[d['master']]['pins'][d['pin']]['max_capacitance']
        direct_electrical.append({'bit':bit,'driver':d,'known_tt_native_input_capacitance':cap,'max_capacitance':float(lim) if lim is not None else None,'unknown_external_port_loads':unknown,'known_load_alone_exceeds_max':lim is not None and cap>float(lim)})
    for r in roots:
        if r['load_count']>32:r['source_support']=sorted(support(r['bit']))
    endpoint_depth=[]
    for k,x in sem[which]['state_correspondence'].items():
        c=cs[k];endpoint_depth.append({'instance':k,'state':x,'D_native_cell_levels':depth(c['connections']['D'][0]),'delay_ps':None})
    out={'scope':'Native mapped source graph; no physical PG ITerm binding or routed electrical claim','master_counts':dict(counts),'all_roots':roots,'all_pg_mterms':pg,'all_cells':cs,'direct_tt_electrical_bounds':direct_electrical,'endpoint_graph_depth':endpoint_depth}
    (P/f'mapped_{which}/census.json').write_text(json.dumps(out,indent=2)+'\n')
    unsafe=[r for r in roots if r['load_count']>32]
    summary[which]={'cells':len(cs),'ff':sum(n for t,n in counts.items() if ls[t]['ff']),'masters':len(counts),'roots':len(roots),'transparent_instances':len(transparent),'declared_pg_mterms':len(pg),'pg_source_graph_bound':sum(x['graph_binding'] is not None for x in pg),'physical_pg_iterm_binding':None,'max_root_loads':max(r['load_count'] for r in roots),'max_native_cell_graph_levels':max(x['D_native_cell_levels'] for x in endpoint_depth),'fault_D_graph_levels':next(x['D_native_cell_levels'] for x in endpoint_depth if x['state']['name']=='fault'),'known_TT_internal_cap_violations':sum(x['known_load_alone_exceeds_max'] for x in direct_electrical),'over32_roots':[{k:r[k] for k in ['driver','load_count','roles']} for r in unsafe]}
(P/'census_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
