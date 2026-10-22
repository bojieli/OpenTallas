"""Private native-source substitution and finite Liberty truth proof; no EDA.

Rebuilds exact source, nine actual source mutants, and the complete all-driver
transparent census. Stable-value proof does not qualify hazards or timing.
"""
import collections, functools, gzip, hashlib, itertools, json, pathlib, re
P=pathlib.Path(__file__).resolve().parent
A=P.parent
(P/'mutants').mkdir(exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(name,x): (P/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def gz(name,b):
    if not isinstance(b,bytes): b=json.dumps(b,sort_keys=True,separators=(',',':')).encode()
    (P/name).write_bytes(gzip.compress(b,mtime=0))
source=gzip.open(A/'qwen_a0_reset_1019/r3/candidate.v.gz','rt').read()
assert sha(source.encode())=='422b8cdacc31dd6cc14cc912cf91a1a037f2de4e09a4875f1a1d9e0749f4f66a'
contracts=json.load(gzip.open(A/'qwen_a0_cut_contract_1019/root_contracts.json.gz'))
abstracts=json.load(gzip.open(A/'qwen_a0_ownership_1019/native_abstracts.json.gz'))['masters']
oldcensus=json.load(gzip.open(A/'qwen_a0_reset_1019/r3/census.json.gz'))
# Reuse the exact expanded bit-expression parser, without model side effects.
parser=(A/'qwen_a0_compact_engine_1019/model.py').read_text()
exec(parser[parser.index('def bits('):parser.index('cells, omitted =')])
cell_pattern=re.compile(r'\\(\S+)\s+\\(\S+)\s+\((.*?)\);',re.S)
pin_pattern=re.compile(r'\.\\(\S+)\s*\((.*?)\)',re.S)
def parse(s):
    result={}
    for m,n,body in cell_pattern.findall(s):
        pp={}
        for p,e in pin_pattern.findall(body):
            ex=connect(p,e); assert not set(ex)&set(pp); pp.update(ex)
        if pp: assert n not in result; result[n]=(m,pp)
    return result
cells=parse(source); assert len(cells)==38609
def outs(m,pp):
    if m in abstracts:
        assert set(pp)=={p for p,i in abstracts[m]['pins'].items() if i['signal_type'] not in ('POWER','GROUND')}
        return {p for p in pp if abstracts[m]['pins'][p]['direction']=='OUTPUT'}
    return set(pp)&{'Y','QN','Q','H','L'}
selected=[r for r in contracts if 'clone_partitions' in r]
assert [len(r['clone_partitions']) for r in selected]==[5,3,2]
replicas=[]; rewires={}
for r in selected:
    n,op=r['driver'].rsplit('/',1); m,pp=cells[n]
    for i,group in enumerate(r['clone_partitions']):
        assert group['INV_parity']==0
        nn=f'a0_private_comb_{n}_{i}'; net=nn+'_out'
        for e in group['native_terminals']:
            assert e not in r['protected_original_terminals'] and e not in rewires
            rewires[e]=net
        replicas.append({'name':nn,'master':m,'root':r['driver'],'pins':{**pp,op:net},'terminals':group['native_terminals']})
assert len(replicas)==10
def emit(reps):
    def edit(match):
        m,n,body=match.groups()
        def pin_edit(pm):
            p,e=pm.groups(); key=n+'/'+p
            return '.\\'+p+' (\\'+rewires[key]+' )' if key in rewires else pm.group(0)
        return '\\'+m+' \\'+n+' ('+pin_pattern.sub(pin_edit,body)+');'
    s=cell_pattern.sub(edit,source)
    extra='\n// PRIVATE ONLY: source-native combinational replicas; not activated.\n'
    for r in reps:
        extra+='wire \\'+r['pins']['Y']+' ;\n'
        extra+='(* keep = 1, dont_touch = 1 *) \\'+r['master']+' \\'+r['name']+' (\n'
        extra+=',\n'.join('  .\\'+p+' (\\'+n+' )' for p,n in r['pins'].items())+'\n);\n'
    assert s.count('endmodule')==1
    return s.replace('endmodule',extra+'endmodule')
candidate=emit(replicas); native=parse(candidate)
assert len(native)==38619
changes=[]
for n,(m,pp) in cells.items():
    nm,np=native[n]; assert nm==m and set(np)==set(pp)
    for p,net in pp.items():
        if np[p]!=net:
            assert rewires[n+'/'+p]==np[p]; changes.append(n+'/'+p)
assert set(changes)==set(rewires)
for r in contracts:
    for e in r['protected_original_terminals']:
        n,p=e.rsplit('/',1); assert native[n][1][p]==cells[n][1][p]
for n,(m,pp) in cells.items():
    if m.startswith(('DFF','TIE')): assert native[n]==cells[n]
gz('private_candidate.v.gz',candidate.encode()); dump('replicas.json',replicas)

# Preserve complete Liberty cell blocks and library hashes, not name-inferred
# Boolean models. Four-state gates evaluate the parsed Liberty function AST.
def block(s,start):
    a=s.index('{',start); depth=1; i=a+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}'); i+=1
    return s[start:i]
libs=A.parent/'uarch/topk_station_SSFF_cell_model_20261002/inputs'
libnames=['asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz']
needed={r['master'] for r in replicas}|{'AND2x2_ASAP7_75t_R','OR3x1_ASAP7_75t_R','NAND3x1_ASAP7_75t_R'}
needed|={m for m,p in cells.values() if m.startswith(('BUF','INV'))}
truth={}; lib_hashes={}; blocks=[]
for filename in libnames:
    raw=(libs/filename).read_bytes(); lib_hashes[filename]=sha(raw); ls=gzip.decompress(raw).decode()
    for match in re.finditer(r'\bcell\s*\(\s*(\S+?)\s*\)\s*\{',ls):
        master=match[1]
        if master not in needed: continue
        body=block(ls,match.start()); blocks.append(body); pins={}; pg={}
        for pm in re.finditer(r'\b(pin|pg_pin)\s*\(\s*(\w+)\s*\)\s*\{',body):
            pb=block(body,pm.start()); role=pm[1]; pin=pm[2]
            if role=='pg_pin':
                pg[pin]=re.search(r'pg_type\s*:\s*(\w+)\s*;',pb)[1]; continue
            direction=re.search(r'direction\s*:\s*(\w+)\s*;',pb)[1]
            f=re.search(r'function\s*:\s*"([^"]+)"\s*;',pb)
            pins[pin]={'direction':direction,'function':f[1] if f else None}
        truth[master]={'pins':pins,'pg_pins':pg,'area_um2':float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1]),'cell_block_sha256':sha(body.encode())}
assert needed==set(truth),needed-set(truth)
gz('native_liberty_cells.lib.gz',('\n\n'.join(blocks)+'\n').encode())
dump('native_liberty.json',{'libraries':lib_hashes,'cells':truth})
def ast(expr):
    tokens=re.findall(r'\w+|[!()+*&|^]',expr); index=0
    assert ''.join(tokens)==re.sub(r'\s+','',expr),expr
    def term():
        nonlocal index
        t=tokens[index]; index+=1
        if t=='!': return ('!',term())
        if t=='(':
            a=level(0); assert tokens[index]==')'; index+=1; return a
        assert re.fullmatch(r'\w+',t); return ('pin',t)
    priorities=[{'+','|'},{'^'},{'*','&'}]
    def level(i):
        nonlocal index
        if i==len(priorities): return term()
        a=level(i+1)
        while index<len(tokens) and tokens[index] in priorities[i]:
            op=tokens[index];index+=1;a=(op,a,level(i+1))
        return a
    result=level(0);assert index==len(tokens);return result
def evaluate(tree,values):
    op=tree[0]
    if op=='pin':return values[tree[1]]
    a=evaluate(tree[1],values)
    if op=='!':return {'0':'1','1':'0','X':'X','Z':'X'}[a]
    b=evaluate(tree[2],values)
    if op in ('*','&'):return '0' if '0' in (a,b) else '1' if a==b=='1' else 'X'
    if op in ('+','|'):return '1' if '1' in (a,b) else '0' if a==b=='0' else 'X'
    assert op=='^';return str(int(a)^int(b)) if a in '01' and b in '01' else 'X'
trees={}
for m,r in truth.items():
    for p,i in r['pins'].items():
        if i['direction']=='output': trees[(m,p)]=ast(i['function'])
tables={}
for m,r in truth.items():
    pins=sorted(p for p,i in r['pins'].items() if i['direction']=='input')
    tables[m]=[{'inputs':dict(zip(pins,vals)), 'outputs':{p:evaluate(trees[m,p],dict(zip(pins,vals))) for p,i in r['pins'].items() if i['direction']=='output'}} for vals in itertools.product('01XZ',repeat=len(pins))]
dump('native_four_state_truth_tables.json',tables)
assert abs(sum(truth[r['master']]['area_um2'] for r in replicas)-0.8748)<1e-12
def graph(cc):
    ds=collections.defaultdict(list);cs=collections.defaultdict(list)
    for n,(m,pp) in cc.items():
        for p,net in pp.items(): (ds if p in outs(m,pp) else cs)[net].append((n,p))
    return ds,cs
def terminal_eval(cc,drivers,terminal,boundary):
    @functools.lru_cache(None)
    def ev(net):
        if net in boundary:return boundary[net]
        assert len(drivers[net])==1,net
        n,op=drivers[net][0];m,pp=cc[n]
        assert (m,op) in trees,(n,m,op)
        return evaluate(trees[m,op],{p:ev(nn) for p,nn in pp.items() if p not in outs(m,pp)})
    n,p=terminal.rsplit('/',1);return ev(cc[n][1][p])
ds,cs=graph(cells);nds,ncs=graph(native)
checks=[]; mutants=[]
for r in selected:
    n,op=r['driver'].rsplit('/',1);m,pp=cells[n]
    inputs={p:net for p,net in pp.items() if p not in outs(m,pp)}
    assert set(inputs)=={p for p,i in truth[m]['pins'].items() if i['direction']=='input'}
    terminals=[e for group in r['clone_partitions'] for e in group['native_terminals']]
    count=0
    for vals in itertools.product('01XZ',repeat=len(inputs)):
        boundary=dict(zip(inputs.values(),vals))
        for e in terminals:
            a=terminal_eval(cells,ds,e,boundary);b=terminal_eval(native,nds,e,boundary)
            assert a==b,(e,boundary,a,b);count+=1
    checks.append({'root':r['driver'],'native_master':m,'input_nets':inputs,'four_state_valuations':4**len(inputs),'terminal_comparisons':count,'all_terminal_equal':True})
    original_rep=next(x for x in replicas if x['root']==r['driver'])
    for mode in ('wrong_master','wrong_input_net','wrong_polarity'):
        reps=json.loads(json.dumps(replicas)); mr=next(x for x in reps if x['name']==original_rep['name'])
        if mode=='wrong_master':mr['master']='OR3x1_ASAP7_75t_R' if m.startswith('AND3') else 'AND2x2_ASAP7_75t_R'
        elif mode=='wrong_polarity':mr['master']='NAND3x1_ASAP7_75t_R' if m.startswith('AND3') else ('OR2x2_ASAP7_75t_R' if m.startswith('NOR') else 'NOR2x1_ASAP7_75t_R')
        else:
            ips=list(inputs);mr['pins'][ips[0]]=inputs[ips[1]]
        ms=emit(reps);mc=parse(ms);md,unused=graph(mc);witness=None; comparisons=0
        for vals in itertools.product('01XZ',repeat=len(inputs)):
            boundary=dict(zip(inputs.values(),vals));e=mr['terminals'][0]
            a=terminal_eval(cells,ds,e,boundary);b=terminal_eval(mc,md,e,boundary);comparisons+=1
            if a!=b:
                witness={'terminal':e,'actual_input_net_values':boundary,'original':a,'mutant':b};break
        assert witness,(mode,m)
        key=n+'_'+mode;gz('mutants/'+key+'.v.gz',ms.encode())
        mutants.append({'case':key,'source_sha256':sha(ms.encode()),'master':mr['master'],'pins':mr['pins'],'actual_DUT_mismatch':witness,'comparisons_until_mismatch':comparisons})
        (P/'mutants'/(key+'.log')).write_text('DUT_MISMATCH '+json.dumps(mutants[-1],sort_keys=True)+'\n')
dump('truth_checks.json',checks);dump('mutant_witnesses.json',mutants)

# Every driver, including each transparent descendant, reset, tie, clock and
# external input. Set-valued DAG closure counts distinct native terminal pins.
ports={kind:re.findall(r'^'+kind+r'\s+\\(\S+)\s*;',source,re.M) for kind in ('input','output')}
assert ports['input'] and ports['output']
port_outputs=set(ports['output'])
def census(cc):
    dd,cons=graph(cc)
    @functools.lru_cache(None)
    def leaves(net):
        result={'PORT/'+net} if net in port_outputs else set()
        for n,p in cons.get(net,[]):
            m,pp=cc[n]
            if m.startswith(('BUF','INV')):
                assert p=='A';result.update(leaves(pp['Y']))
            else:result.add(n+'/'+p)
        return frozenset(result)
    rows=[]
    for net in sorted(set(dd)|set(ports['input'])):
        for n,p in dd.get(net,[(None,net)]):
            master=cc[n][0] if n else 'INPUT_PORT'; endpoints=sorted(leaves(net))
            # Frozen native census counts ITerm input loads as direct; output
            # ports are included only in the transparent terminal count.
            direct=len(cons.get(net,[]))
            rows.append({'driver':n+'/'+p if n else 'PORT/'+p,'master':master,'net':net,'direct':direct,'transparent_loads':len(endpoints),'endpoints':endpoints,'clock':net.startswith('ck') or any(e.endswith(('/CLK','/clk')) for e in endpoints),'sequential':master.startswith('DFF')})
    return rows
before=census(cells);after=census(native)
oldmap={r['driver']:r for r in oldcensus['all_drivers']};bm={r['driver']:r for r in before};am={r['driver']:r for r in after}
assert set(bm)==set(oldmap),(len(bm),len(oldmap),set(bm)^set(oldmap))
for n,r in bm.items():
    assert r['direct']==oldmap[n]['direct'] and r['transparent_loads']==oldmap[n]['transparent_loads'],(n,r['direct'],r['transparent_loads'],oldmap[n]['direct'],oldmap[n]['transparent_loads'])
    assert set(r['endpoints'])==set(oldmap[n]['endpoints']),n
delta=[]
for n,r in am.items():
    b=bm.get(n)
    if not b or r['direct']!=b['direct'] or r['transparent_loads']!=b['transparent_loads']:
        delta.append({'driver':n,'master':r['master'],'before_direct':b['direct'] if b else None,'after_direct':r['direct'],'before_transparent':b['transparent_loads'] if b else None,'after_transparent':r['transparent_loads'],'added_terminals':sorted(set(r['endpoints'])-set(b['endpoints'] if b else [])),'removed_terminals':sorted(set(b['endpoints'] if b else [])-set(r['endpoints']))})
unsafe=lambda rows:[r for r in rows if not r['clock'] and max(r['direct'],r['transparent_loads'])>32]
gz('all_drivers_before.json.gz',before);gz('all_drivers_after.json.gz',after);gz('census_delta.json.gz',delta);gz('unsafe_after.json.gz',unsafe(after))
inc=collections.Counter()
for r in replicas:
    for p,net in r['pins'].items():
        if p!='Y':inc[net]+=1
assert sum(inc.values())==22
for r in replicas:assert am[r['name']+'/Y']['transparent_loads']<=32
summary={'status':'PRIVATE_SOURCE_STABLE_VALUE_PROOF_ONLY_PHYSICAL_HOLD','input_source_sha256':sha(source.encode()),'private_source_sha256':sha(candidate.encode()),'cells_before':len(cells),'cells_after':len(native),'new_native_comb_cells':10,'new_state_bits':0,'new_clock_pins':0,'new_logical_edges':0,'mapped_added_area_um2':0.8748,'rewired_native_terminals':len(rewires),'four_state_terminal_comparisons':sum(x['terminal_comparisons'] for x in checks),'real_source_mutants_with_DUT_mismatch':len(mutants),'full_baseline_census_roundtrip_rows':len(before),'all_driver_rows_after':len(after),'unsafe_nonclock_rows_before':len(unsafe(before)),'unsafe_nonclock_rows_after':len(unsafe(after)),'sequential_unsafe_after':[{k:r[k] for k in ('driver','direct','transparent_loads')} for r in unsafe(after) if r['sequential']],'added_upstream_input_loads':dict(inc),'new_upstream_nonclock_unsafe':[{'driver':r['driver'],'before':bm[r['driver']]['transparent_loads'],'after':r['transparent_loads']} for r in unsafe(after) if r['driver'] in bm and max(bm[r['driver']]['direct'],bm[r['driver']]['transparent_loads'])<=32],'all_sequential_instances_and_reset_ties_unchanged':True,'canonical_protected_terminals_unchanged':True,'native_timing_hazards_reset_recovery_clock_phase_PG_parent_fit':'UNQUALIFIED','public_activation':False}
dump('summary.json',summary)
inputs=[A/'qwen_a0_reset_1019/r3/candidate.v.gz',A/'qwen_a0_reset_1019/r3/census.json.gz',A/'qwen_a0_cut_contract_1019/root_contracts.json.gz',A/'qwen_a0_compact_engine_1019/model.py',A/'qwen_a0_ownership_1019/native_abstracts.json.gz']+[libs/n for n in libnames]
dump('input_hashes.json',{str(p.relative_to(A.parent.parent)):sha(p.read_bytes()) for p in inputs})
classification=lambda r:'sequential' if r['sequential'] else 'tie' if r['master'].startswith('TIE') else 'transparent_BUF_INV' if r['master'].startswith(('BUF','INV')) else 'logic'
dump('unsafe_classification.json',{'before':dict(collections.Counter(classification(r) for r in unsafe(before))),'after':dict(collections.Counter(classification(r) for r in unsafe(after))),'removed_unsafe_rows':[{'driver':r['driver'],'master':r['master'],'before_transparent':r['transparent_loads'],'after_transparent':am[r['driver']]['transparent_loads']} for r in unsafe(before) if max(am[r['driver']]['direct'],am[r['driver']]['transparent_loads'])<=32],'worsened_upstream_rows':[d for d in delta if d['before_transparent'] is not None and d['after_transparent']>d['before_transparent']]})
print(json.dumps(summary,indent=2))
