from pathlib import Path
import tkinter,collections,json,functools,sys,gzip
p=Path(__file__).parent;t=tkinter.Tcl();alias={}
def read_text(name):
 f=p/name
 return f.read_text() if f.exists() else gzip.open(str(f)+'.gz','rt').read()
for line in read_text('control16_replica_manifest.tcl').splitlines():
 a=t.splitlist(line)
 if len(a)==3 and a[1]=='::ot_control_copy_aliases':
  v=t.splitlist(a[2]);alias=dict(zip(v[::2],v[1::2]))
def root(n):
 seen=set()
 while n in alias:
  assert n not in seen;seen.add(n);n=alias[n]
 return n
masters={};inputs=collections.defaultdict(dict);outputs={}
for line in read_text(sys.argv[1] if len(sys.argv)>1 else 'control16_actual_startup_equations.tsv').splitlines():
 a=line.split('\t')
 if a[0]=='MASTER':masters[a[1]]=a[2]
 elif a[0]=='INPUT':inputs[a[1]][a[2]]=tuple(t.splitlist(a[3]))
 elif a[0]=='OUTPUT':outputs[a[1]]=tuple(t.splitlist(a[2]))
def ff(n):return masters[n].startswith(('DFF','SDFF'))
pending=set();errors=[]
@functools.lru_cache(None)
def deps(a,b):
 if a==b:return frozenset()
 if a[0]!='CELL' or b[0]!='CELL' or a[2:]!=b[2:]:
  raise ValueError(('leaf_or_polarity_mismatch',a,b))
 x,y=a[1],b[1]
 if masters[x]!=masters[y] or root(x)!=root(y):raise ValueError(('source_master_mismatch',x,y))
 if ff(x):
  k=tuple(sorted((x,y)));pending.add(k);return frozenset([k])
 if inputs[x].keys()!=inputs[y].keys():raise ValueError(('ABI',x,y))
 return frozenset().union(*(deps(inputs[x][pin],inputs[y][pin]) for pin in inputs[x]))
newffs=[n for n in masters if n in alias and ff(n)];initial={n:tuple(sorted((n,root(n)))) for n in newffs}
pending.update(initial.values());graph={};by_pin={}
while pending:
 k=pending.pop()
 if k in graph:continue
 x,y=k
 try:
  pd={pin:deps(inputs[x][pin],inputs[y][pin]) for pin in inputs[x]}
  by_pin[k]=pd;graph[k]=set().union(*pd.values())
 except ValueError as e:errors.append(str(e));graph[k]={k}
levels={};changed=True
while changed:
 changed=False
 for k,v in graph.items():
  if k not in levels and all(d in levels for d in v):levels[k]=1+max([levels[d] for d in v] or [0]);changed=True
hist=collections.Counter(levels[initial[n]] for n in newffs if initial[n] in levels)
unresolved=[n for n in newffs if initial[n] not in levels]
def detail(n):
 k=initial[n]
 return dict(copy=n,source=root(n),master=masters[n],capture_bound_edges=levels.get(k),pair_dependencies=[list(x) for x in sorted(graph[k])],input_pair_dependencies={pin:[list(x) for x in sorted(ds)] for pin,ds in by_pin.get(k,{}).items()})
r=dict(verdict='DIAGNOSTIC_ONLY',pair_dependency_result='PASS' if not errors and not unresolved else 'FAIL',method='Actual unaliased graph pair dependency. Exact combinational congruence; one edge per FF-pair dependency. No reset/enable value assumptions or zero initial states.',new_ff_count=len(newffs),finite_bound_histogram=dict(sorted(hist.items())),unresolved_count=len(unresolved),errors=errors,qualifications=['Finite capture bound assumes both corresponding clocks deliver the same legal edge and all controls meet native timing. It does not prove valid observability begins later than the bound.','Unresolved feedback pairs need actual qualified-write/validity lifetime proof; a structural cycle alone is not a counterexample.','Asynchronous assertion/deassertion and abort/restart first-valid joins are not established by this data dependency census.'],copies=[detail(n) for n in sorted(newffs)])
(p/('control16_startup_pair_dependencies_mutant.json' if len(sys.argv)>1 else 'control16_startup_pair_dependencies.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='copies'},indent=2))
print('unresolved source families',collections.Counter(root(n).split('[')[0] for n in unresolved).most_common(24))
