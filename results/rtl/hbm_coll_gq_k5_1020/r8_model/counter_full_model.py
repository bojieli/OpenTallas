import pathlib,sys,json,re,hashlib,gzip,collections
sys.path[:0]=['/src/tools','/src/tools/ref_tile'];import textbook_lint as T;import native_census as N
R=pathlib.Path('/audit');D=pathlib.Path('/work');orig=json.load(open(D/'native_census_r7.json'));roles,receipts=N.liberty_roles([x['path'] for x in orig['liberty']]);mods=T.parse_verilog(pathlib.Path(orig['netlist']['path']).read_text());mods={k:v for k,v in mods.items() if k==orig['top'] or k not in roles};g,_=T.flatten(mods,orig['top'])
oldcells=list(g.cells);drivers={};loads=collections.defaultdict(list)
for i,(m,n,ps) in enumerate(g.cells):
 for pn,ns in ps.items():
  d=roles[m]['pins'].get(pn,{}).get('direction')
  for net in ns:
   if d=='output':drivers[g.find(net)]=(i,pn)
   elif d=='input':loads[g.find(net)].append((i,pn))
def ffword(var):
 out={}
 for m,n,ps in g.cells:
  mm=re.match(r'u_ot_pr_core\.'+var+r'\[(\d+)\]\$_',n)
  if not mm:continue
  op=[g.find(ns[0]) for pn,ns in ps.items() if roles[m]['pins'].get(pn,{}).get('direction')=='output'];assert len(op)==1
  out[int(mm[1])]=op[0]
 assert sorted(out)==list(range(16)),(var,out)
 return [out[i] for i in range(16)]
per,tl,lps=[ffword(v) for v in ['per','tl','lps']]
# These are actual mapped R7 module boundaries; all eight external Q nets are retained.
prefs=sorted(set(n[:n.index('.u_wrap.')+7] for _,n,_ in g.cells if '.u_wrap.' in n));assert len(prefs)==8,prefs
remove=set();qouts=[]
for pref in prefs:
 ids={i for i,(_,n,_) in enumerate(g.cells) if n.startswith(pref)};assert ids
 outs=set()
 for i in ids:
  m,n,ps=g.cells[i]
  for pn,ns in ps.items():
   if roles[m]['pins'].get(pn,{}).get('direction')=='output':
    for net in ns:
     if any(j not in ids for j,_ in loads[g.find(net)]):outs.add(g.find(net))
 assert len(outs)==1,(pref,len(outs));qouts.append(next(iter(outs)));remove|=ids
new=[];num=0
# Select only real TT/FF-compatible Liberty gates, and independently check their exact truth tables.
def gate_master(prefix,expected):
 for m in sorted(roles):
  rp=roles[m]['pins']
  if not m.startswith(prefix) or roles[m]['sequential'] or 'Y' not in rp:continue
  inputs=[p for p,r in rp.items() if r['direction']=='input'];want=['A'] if prefix=='INV' else ['A','B']
  if sorted(inputs)!=want:continue
  f=rp['Y'].get('function')
  if not f:continue
  e=f.replace('!',' not ').replace('*',' and ').replace('+',' or ')
  if not re.fullmatch(r'[AB() \tandort]+',e):continue
  if all(bool(eval(e,{'__builtins__':{}},{'A':bool(a),'B':bool(b)}))==bool(expected(a,b)) for a in [0,1] for b in [0,1]):return m
 raise ValueError('no exact real Liberty gate '+prefix)
M={'inv':gate_master('INV',lambda a,b:not a),'and':gate_master('AND2',lambda a,b:a and b),'or':gate_master('OR2',lambda a,b:a or b),'xor':gate_master('XOR2',lambda a,b:a!=b),'xnor':gate_master('XNOR2',lambda a,b:a==b)}
def add(kind,ins,out=None):
 global num
 num+=1;out=g.net('__MODEL_R8_'+str(num)) if out is None else out;ps={'A':[ins[0]],'Y':[out]}
 if len(ins)==2:ps['B']=[ins[1]]
 new.append((M[kind],'__MODEL_R8_'+str(num),ps));return out
def tree(kind,ns):
 while len(ns)>1:ns=[add(kind,ns[i:i+2]) if i+1<len(ns) else ns[i] for i in range(0,len(ns),2)]
 return ns[0]
# Full 16-bit modulo subtract-one, shared ONCE; no new sequential state or assumed FF relation.
last=[add('inv',[per[0]])];borrow=last[0]
for i in range(1,16):
 last.append(add('xor',[per[i],borrow]))
 if i<15:borrow=add('and',[borrow,add('inv',[per[i]])])
more=tree('or',lps[1:])
for q in qouts:
 eq=tree('and',[add('xnor',[tl[i],last[i]]) for i in range(16)]);add('and',[eq,more],q)
# Exhaustive arithmetic identity of the proposed shared subtract cone, including per=0 wraparound.
for value in range(65536):
 bits=[(value>>i)&1 for i in range(16)];res=1-bits[0];b=1-bits[0]
 for i in range(1,16):res|=(bits[i]^b)<<i;b=b&(1-bits[i])
 assert res==((value-1)&65535)
g.cells=[c for i,c in enumerate(g.cells) if i not in remove]+new
# Refuse any mutation outside the exact eight combinational wrapper cones.
untouched_before=hashlib.sha256(repr([c for i,c in enumerate(oldcells) if i not in remove]).encode()).hexdigest();untouched_after=hashlib.sha256(repr(g.cells[:-len(new)]).encode()).hexdigest();assert untouched_before==untouched_after
report=N.census(g,roles);tracked=[v for v in report['driver_counts'] if any(x in v['driver'] for x in ['.per[','.tl[','.lps[','.g_base_copy[','stored_base','rst_n'])]
# Actual cell-area inventory from the exact Liberty files. Corner copies must agree for area.
areas={}
for rr in receipts:
 p=pathlib.Path(rr['path']);raw=p.read_bytes();s=(gzip.decompress(raw) if p.suffix=='.gz' else raw).decode();s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
 for kind,_,body in N.groups(s):
  if kind!='library':continue
  for k,m,cb in N.groups(body):
   if k=='cell' and N.attr(cb,'area') is not None:areas[m]=float(N.attr(cb,'area'))
missing=sorted(set(m for m,_,_ in g.cells)-set(areas));assert not missing,missing
out={k:v for k,v in report.items() if k!='driver_counts'};out.update(schema='opentallas.gq_r8_full_mapped_cone_model.v1',qualification=False,engine_patch=False,scope='MODEL ONLY exact R7 full graph with ONLY eight wrap cones replaced by shared subtract + explicit equality gates; period/flat/AQ failures remain visible',original_netlist=orig['netlist'],actual_liberty=receipts,primitive_truth_tables='PASS real functions all4 input cases',subtract_identity='PASS all65536 modulo16bit values',removed_cells=len(remove),added_cells=len(new),added_FF=0,added_boot_edges=0,added_data_edges=0,untouched_graph_sha256=untouched_before,actual_all_roles_errors=len(report['role_errors']),tracked_complete_driver_counts=tracked,model_area_um2=sum(areas[m] for m,_,_ in g.cells),model_sequential_area_um2=sum(areas[m] for m,_,_ in g.cells if roles[m]['sequential']),primitive_masters=M)
(R/'r8_counter_full_model.json').write_text(json.dumps(out,indent=2)+'\n');print('R8_COUNTER_MODEL',report['status'],'max',report['max_dynamic_loads'],'viol',len(report['violations']),'roles',len(report['role_errors']),'removed',len(remove),'added',len(new),flush=True)
for v in report['violations']:print(v['driver'],v['loads'],flush=True)
