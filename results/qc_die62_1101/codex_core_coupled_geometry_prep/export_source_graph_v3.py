"""Read-only actual mapped-Yosys JSON graph; eight folds become opaque cuts.

No RTL generation or synthesis. Run with ot-run8GB1T, JSON and outputdir args.
"""
import collections,gzip,hashlib,json,sys,time
from pathlib import Path
sys.setrecursionlimit(10000)
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
data=json.loads(src.read_text());mods=data['modules'];top='qfd_qc_coll_core_part'
hard={'ot_coll_fold_slice','ot_sram_1r1w2c_64x546_m1','ot_sram_1r1w_32x546_m1','ot_sram_1r1w_512x128_m4_r2c2','ot_sram_1r1w_64x512_m1_r2c2'}
parents=[];nodes=[];topinputs={};alias_count=0
def new():
    n=len(parents);parents.append(n);return n
def find(n):
    if not isinstance(n,int)or n<0:return n
    while parents[n]!=n:parents[n]=parents[parents[n]];n=parents[n]
    return n
def unite(a,b):
    global alias_count
    a,b=find(a),find(b)
    if a==b:return
    if not isinstance(a,int)or not isinstance(b,int):raise ValueError(('constant_alias',a,b))
    parents[b]=a;alias_count+=1
def descend(typ,prefix,bindings):
    m=mods[typ];ns={}
    def net(n):
        if not isinstance(n,int):return n
        if n not in ns:ns[n]=new()
        return find(ns[n])
    for pname,conn in bindings.items():
        bits=m['ports'][pname]['bits'];assert len(bits)==len(conn),(typ,pname)
        for a,b in zip(bits,conn):
            if a in ns:unite(ns[a],b)
            else:ns[a]=b
    if not prefix:
        for pn,pp in m['ports'].items():
            if pp['direction']=='input':
                for j,b in enumerate(pp['bits']):topinputs[net(b)]=(pn,j)
    for name,c in m.get('cells',{}).items():
        ct=c['type'];path=prefix+name;conn={pn:[net(b)for b in bits]for pn,bits in c['connections'].items()}
        cm=mods.get(ct);dirs=c.get('port_directions')or({pn:v['direction']for pn,v in cm['ports'].items()}if cm else{})
        if ct not in hard and cm and cm.get('cells') and '_ASAP7_' not in ct:
            descend(ct,path+'.',conn)
        else:nodes.append(dict(name=path,type=ct,connections=conn,directions=dirs))
descend(top,'',{})
topinputs={find(k):v for k,v in topinputs.items()}
counts=collections.Counter(n['type']for n in nodes);assert sum(counts[n]for n in hard)==29,counts
print('CLASSIFY_ACTUAL',len(nodes),counts.most_common(20),flush=True)
assert len(nodes)==215626,len(nodes)
drivers={};multiple=[];ffs=set();macro=set();terms=[];termmap={}
def term(key):
    if key not in termmap:termmap[key]=len(terms);terms.append(key)
    return termmap[key]
for i,n in enumerate(nodes):
    if n['type']in hard:macro.add(i)
    elif 'DFF'in n['type'].upper()or'SDF'in n['type'].upper():
        assert 'D'in n['connections']and any(p in n['connections']for p in ['Q','QN']),n
        ffs.add(i)
    for pn,bs in n['connections'].items():
        n['connections'][pn]=bs=[find(b)for b in bs]
        if n['directions'].get(pn)!='output':continue
        for j,b in enumerate(bs):
            if not isinstance(b,int):continue
            if b in drivers and drivers[b]!=(i,pn,j):multiple.append([b,drivers[b],[i,pn,j]])
            drivers[b]=(i,pn,j)
assert not multiple,multiple[:5]
memo={};active=set();cycles=[];undriven=set()
def sources(b):
    if not isinstance(b,int):return frozenset([term(('CONST',b))])
    if b in memo:return memo[b]
    if b in active:
        cycles.append(b);return frozenset([term(('CYCLE',b))])
    if b not in drivers:
        if b in topinputs:return frozenset([term(('TOP',)+topinputs[b])])
        undriven.add(b);return frozenset([term(('UNDRIVEN',b))])
    i,pn,j=drivers[b]
    if i in ffs:return frozenset([term(('FF',i,pn,j))])
    if i in macro:return frozenset([term(('MACRO',i,pn,j))])
    active.add(b);z=set();n=nodes[i]
    for p,bs in n['connections'].items():
        if n['directions'].get(p)=='input':
            for a in bs:z.update(sources(a))
    active.remove(b);memo[b]=frozenset(z);return memo[b]
capture=[];allff={};macroinput=[];relevant=set()
for i in sorted(ffs):
    fan=set()
    for b in nodes[i]['connections']['D']:fan.update(sources(b))
    allff[i]=sorted(fan)
    if any(terms[z][0]=='MACRO'for z in fan):capture.append(dict(capture_ff=i,sources=sorted(fan)));relevant.add(i)
for i in sorted(macro):
    for pn,bs in nodes[i]['connections'].items():
        if nodes[i]['directions'].get(pn)!='input':continue
        for j,b in enumerate(bs):
            fan=sources(b);macroinput.append(dict(macro=i,port=pn,bit=j,sources=sorted(fan)))
            relevant.update(terms[z][1]for z in fan if terms[z][0]=='FF')
packet=dict(status='ACTUAL_SOURCE_GRAPH_ONLY_NO_GEOMETRY_CREDIT',source=str(src),top=top,opaque_macro_count=29,standard_leaf_count=len(nodes)-29,standard_FF_count=len(ffs),hierarchy_alias_unions=alias_count,multiple_drivers=multiple,cycles=cycles,undriven_nets=sorted(undriven),leaf_types=dict(counts),terms=terms,macro_nodes={str(i):nodes[i]for i in sorted(macro)},ff_nodes={str(i):dict(name=nodes[i]['name'],type=nodes[i]['type'],connections=nodes[i]['connections'])for i in sorted(ffs)},macro_to_first_capture=capture,macro_input_sources=macroinput,relevant_ff_input_sources={str(i):allff[i]for i in sorted(ffs)},scope='Exact actual mapped combinational dependencies; FF D is capture endpoint and Q/QN are boundaries. Any cycle/undriven retains HOLD. Functional arithmetic/clock/reset/timing not proved. No new RTL or EDA.')
with gzip.open(out/'MACRO_FF_SOURCE_GRAPH.json.gz','wt')as f:json.dump(packet,f,separators=(',',':'))
summary={k:v for k,v in packet.items()if k in ['status','source','top','opaque_macro_count','standard_leaf_count','standard_FF_count','hierarchy_alias_unions']};summary.update(capture_rows=len(capture),macro_input_bit_rows=len(macroinput),relevant_ff_nodes=len(relevant),cycles=len(cycles),undriven=len(undriven),output_bytes=(out/'MACRO_FF_SOURCE_GRAPH.json.gz').stat().st_size)
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
