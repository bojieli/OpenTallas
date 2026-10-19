"""Analytical useful-producer replication; no emitted RTL or netlist mutation.

Run on fleet. BUF/INV are transparent to logical load accounting. Copy demand
propagates through D/control/reset inputs as well as arithmetic inputs until a
fixed point; clocks are priced separately. Every native consumer pin is kept.
"""
import collections, gzip, hashlib, importlib.util, json, math, pathlib, re, sys

def family(name):
    if name.startswith('u_rst.'): return 'reset'
    if name.startswith('_'): return 'flattened_boolean'
    if '.g_safe_decode.' in name: return 'sinkhorn.predecode'
    if '.g_t[' in name: return 'sinkhorn.denominator'
    if '.u_seed.' in name: return 'sinkhorn.seed'
    if '.g_q[' in name: return 'sinkhorn.quotient'
    if '.u_sinkh.' in name:
        n=name.split('.u_sinkh.',1)[1]
        if n.startswith('g_row'): return 'sinkhorn.row_add_normalize'
        if n.startswith('g_z.'): return 'sinkhorn.step0_eps'
        return 'sinkhorn.' + re.split(r'\[|\$|\.',n)[0]
    if 'u_mul' in name: return 'multiplier'
    return 'other.'+name.split('[',1)[0].split('$',1)[0]

def main():
    root=pathlib.Path(sys.argv[1]); spec=importlib.util.spec_from_file_location('lint',root/'lint.py')
    lint=importlib.util.module_from_spec(spec);sys.modules['lint']=lint;spec.loader.exec_module(lint)
    net=root/'1_2_yosys.v.gz'; text=gzip.open(net,'rt').read()
    g,top=lint.flatten(lint.parse_verilog(text),'dsdv_gunit_l5');a=lint.build(g,None)
    clk,_=lint.clock_nets(g,a); kinds=a['kind'];drv=a['driver']; const={g.find(i) for i in range(4)}
    # Exact library cell area and clock input capacitance from pinned ORFS TT libs.
    areas={};caps={};libhash={}
    for p in sorted(p for p in (root/'libs').iterdir() if '_RVT_TT_' in p.name and ('nldm_211120' in p.name or 'nldm_220122' in p.name or 'nldm_220123' in p.name)):
        libhash[p.name]=hashlib.sha256(p.read_bytes()).hexdigest();s=(gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text())
        for m in re.finditer(r'cell\s*\(\s*(\S+?)\s*\)\s*\{',s):
            start=m.end();depth=1;end=start
            while depth and end<len(s):
                depth+=(s[end]=='{')-(s[end]=='}');end+=1
            body=s[start:end]; ar=re.search(r'\barea\s*:\s*([\d.eE+-]+)',body)
            if ar: areas[m.group(1)]=float(ar.group(1))
            ck=re.search(r'pin\s*\(\s*CLK\s*\).*?capacitance\s*:\s*([\d.eE+-]+)',body,re.S)
            if ck:caps[m.group(1)]=float(ck.group(1))
    memo={}
    def origin(x):
        if x in memo:return memo[x]
        d=drv.get(x)
        if d and d[0]>=0 and kinds[d[0]]=='buf':
            ins=list(lint._in_nets(g,a,d[0]));assert len(ins)==1,(g.cells[d[0]],ins)
            v=origin(ins[0])
        else:v=x
        memo[x]=v;return v
    edges=collections.defaultdict(list)
    for ci,(typ,nm,pins) in enumerate(g.cells):
        if kinds[ci] in ('buf','phys','tie'):continue
        for pn,bs in pins.items():
            if a['pin_dir'][ci][pn]!='in' or pn in lint.SEQ_CLK_PINS:continue
            for x in bs:
                rt=origin(x)
                if rt not in const and rt not in clk:edges[rt].append((ci,pn))
    for x,ports in a['out_ports'].items():
        for p in ports:edges[origin(x)].append((-1,p))
    replicas=[1]*len(g.cells); history=[]
    for iteration in range(200):
        changed=0;updates=replicas.copy()
        for x,loads in edges.items():
            d=drv.get(x)
            if not d or d[0]<0:continue
            ci=d[0]
            if kinds[ci] in ('buf','tie','phys'):continue
            demand=sum(replicas[c] if c>=0 else 1 for c,p in loads)
            needed=max(1,math.ceil(demand/24))
            if needed>updates[ci]:updates[ci]=needed;changed+=1
        history.append({'iteration':iteration,'changed':changed,'extra_cells':sum(updates)-len(updates)})
        replicas=updates
        if not changed:break
    else:raise RuntimeError('No fixed point; reject model')
    inventory=collections.defaultdict(lambda:collections.Counter())
    for ci,(typ,nm,pins) in enumerate(g.cells):
        if kinds[ci]=='ff':
            inv=inventory[family(nm)];inv['flops']+=1;inv['reset_flops']+=('DFFASR' in typ);inv['extra_copy_flops']+=replicas[ci]-1
    rows=[];groups=collections.defaultdict(lambda:collections.Counter());ports=[];missing=set()
    for x,loads in edges.items():
        d=drv.get(x);demand=sum(replicas[c] if c>=0 else 1 for c,p in loads)
        if not d or d[0]<0:
            if demand>24:ports.append({'net':g.net_name[x],'loads':len(loads),'expanded_loads':demand})
            continue
        ci,pn=d;typ,nm,_=g.cells[ci];cp=replicas[ci]
        if kinds[ci] in ('buf','tie','phys'):continue
        if len(loads)<=32 and cp==1:continue
        ar=areas.get(typ)
        if ar is None:missing.add(typ);ar=0
        f=family(nm);q=groups[f];q['original_offenders']+=len(loads)>32;q['model_roots']+=1
        q['original_pins']+=len(loads);q['expanded_pins']+=demand;q['extra_cells']+=cp-1
        q['extra_ff']+=(cp-1)*(kinds[ci]=='ff');q['added_native_area_um2']+=(cp-1)*ar
        rows.append({'driver':nm,'master':typ,'family':f,'kind':kinds[ci], 'original_loads':len(loads),
          'expanded_loads':demand,'replicas':cp,'max_group_pins':math.ceil(demand/cp),
          'extra_area_um2':(cp-1)*ar,'consumer_pin_classes':dict(collections.Counter(p for c,p in loads)),
          'consumer_families':dict(collections.Counter(family(g.cells[c][1]) if c>=0 else 'port' for c,p in loads))})
    assert not missing,missing
    assert all(r['max_group_pins']<=24 for r in rows), [r for r in rows if r['max_group_pins']>24]
    base_area=sum(areas[t] for t,n,p in g.cells if t in areas)
    extra=sum(r['extra_area_um2'] for r in rows)
    ffextra=sum(replicas[i]-1 for i,k in enumerate(kinds) if k=='ff')
    clkextra=sum((replicas[i]-1)*caps.get(g.cells[i][0],0) for i,k in enumerate(kinds) if k=='ff')
    # Restore both original Q and inverse-Q polarity at each NEW useful producer.
    # Original transparent cells remain in baseline; two INVx1 per replica is
    # conservative against the actual original polarity paths, not a load waiver.
    polarity_cells=2*sum(replicas[i]-1 for i,k in enumerate(kinds) if k not in ('buf','tie','phys'))
    polarity_area=polarity_cells*areas['INVx1_ASAP7_75t_R']
    result={'status':'MODEL_ONLY_NOT_BUILD_ADMISSION','source':'12ab196b6','evidence':'3ca0d8055',
      'netlist_sha256':hashlib.sha256(net.read_bytes()).hexdigest(),'lib_sha256':libhash,
      'target_logical_pins':24,'original_cells':len(g.cells),'original_ff':sum(k=='ff' for k in kinds),
      'fixed_point_history':history,'storage_inventory':dict(inventory),'groups':dict(groups),'all_roots':rows,'unrepairable_input_ports':ports,
      'base_native_area_um2':base_area,'added_native_area_um2':extra,'added_ff':ffextra,
      'added_ff_clock_cap_lib_units':clkextra,'polarity_allowance_cells':polarity_cells,
      'polarity_allowance_um2':polarity_area,'conservative_total_area_um2':base_area+extra+polarity_area,
      'buffer_inv_transparent':True,'runtime_storage_sram_and_fault_pipeline_not_included':True}
    (root/'whole_model.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('all_roots','lib_sha256','groups')},indent=2))
    print(json.dumps(result['groups'],indent=2))

if __name__=='__main__':main()
