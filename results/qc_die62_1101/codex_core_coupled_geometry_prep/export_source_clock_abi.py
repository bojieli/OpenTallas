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

clock=collections.defaultdict(list);macroclocks=[]
for i,n in enumerate(nodes):
 if 'DFF'in n['type']:
  ck=n['connections'].get('CLK',n['connections'].get('CK',[]));assert len(ck)==1
  bit=find(ck[0]);clock[bit].append(dict(node=i,name=n['name'],type=n['type']))
 if n['type']in hard:
  for pn in ['clk','rclk','wclk']:
   if pn in n['connections']:
    bs=[find(x)for x in n['connections'][pn]];assert len(bs)==1
    macroclocks.append(dict(inst=n['name'],module=n['type'],clock_pin=pn,canonical_bit=bs[0],top_input=topinputs.get(bs[0])))
rows=[]
for bit,ff in sorted(clock.items()):rows.append(dict(canonical_bit=bit,top_input=topinputs.get(bit),FF_count=len(ff),FF_types=dict(collections.Counter(x['type']for x in ff)),FF_node_ids=[x['node']for x in ff],examples=[x['name']for x in ff[:3]]))
models={}
for typ in {x['type']for ff in clock.values()for x in ff}:
 mm=mods.get(typ,{})
 models[typ]={'model_cells':[{'type':c['type'],'parameters':c.get('parameters',{})}for c in mm.get('cells',{}).values()],'attributes':mm.get('attributes',{})}
packet={'status':'ACTUAL_SOURCE_CLOCK_NET_ABI_ONLY_NO_PHASE_TIMING','top':top,'metadata_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'actual_standard_FFs':sum(len(ff)for ff in clock.values()),'clock_net_cohorts':rows,'macro_clock_bindings':macroclocks,'selected_cell_functional_models':models,'clock_pin_native_placement_and_phase_qualification':False,'scope':'CanonicalbitID→actualtopinput fromsamehierarchyaliasunion usedbyDATAgraph; no name/phase aliases. Physical8normalgridrewire, forwardedclockdomains, Libertyclocked_on/polarity, skew, reset/START/CA/boot remain independent.'}
(out/'ACTUAL_CLOCK_SOURCE_ABI.json').write_text(json.dumps(packet,indent=2)+'\n');print('SOURCECLOCKABI',len(rows),'cohorts',packet['actual_standard_FFs'],'FFs',sum(r['top_input']is None for r in rows),'unbound')
