"""HB1 immutable endpoint capacity/source-retention model. No RTL/tools/jobs."""
import collections, functools, gzip, hashlib, json, math, pathlib, re, sys
H=pathlib.Path(__file__).resolve().parent
P=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else H.parent/'s81_hb1_diagnostic_census_1019/receipt/native_census.json.gz'; d=json.load(gzip.open(P,'rt'))
rs=[r for r in d['records'] if r['role'] not in ('transparent','clock')]
by={r['driver']:r for r in rs if r['role']!='input'}
assert len(by)==len(rs)-sum(r['role']=='input' for r in rs)
incoming=collections.defaultdict(dict)
for r in rs:
 assert len(r['endpoints'])==len(r['terminal_inversions'])==r['count']
 name=r['net'] if r['role']=='input' else r['driver']
 for (dst,pin),inv in zip(r['endpoints'],r['terminal_inversions']):
  assert pin not in incoming[dst],(dst,pin)
  incoming[dst][pin]=dict(source=name,role=r['role'],master=r['master'],inverted=inv)
copies={n:1 for n in by}; rounds=[]
for it in range(100):
 nxt={n:max(copies[n],math.ceil(sum(copies.get(dst,1) for dst,p in r['endpoints'])/32)) for n,r in by.items()}
 rounds.append(sum(v-1 for v in nxt.values()))
 if nxt==copies:break
 copies=nxt
else:raise AssertionError('no fixedpoint')
@functools.lru_cache(None)
def ancestors(n):
 if n not in by or by[n]['role']!='comb':return frozenset([n])
 return frozenset().union(*(ancestors(x['source']) for x in incoming[n].values()))
rows=[]; assignments=[]
for n,r in by.items():
 if copies[n]==1:continue
 es=[(dst,k,p,inv) for (dst,p),inv in zip(r['endpoints'],r['terminal_inversions']) for k in range(copies.get(dst,1))]
 counts=collections.Counter()
 for ix,(dst,k,p,inv) in enumerate(es):
  src=ix//32;counts[src]+=1
  assignments.append([n,src,dst,k,p,inv])
 assert max(counts.values())<=32
 rows.append(dict(driver=n,role=r['role'],master=r['master'],copies=copies[n],original_pins=r['count'],expanded_pins=len(es),copy_pin_counts=[counts[k] for k in range(copies[n])],incoming=incoming[n],sequential_ancestors=sorted(ancestors(n)),area_um2=(copies[n]-1)*d['area_by_master'][r['master']]))
inputs=[dict(port=r['net'],expanded_pins=sum(copies.get(dst,1) for dst,p in r['endpoints'])) for r in rs if r['role']=='input']
assert max(r['expanded_pins'] for r in inputs)<=32
# Full residual audit, not only the original 73 unsafe roots.
assert all(sum(copies.get(dst,1) for dst,p in r['endpoints'])<=32*copies[n] for n,r in by.items())
extra={role:sum(r['copies']-1 for r in rows if r['role']==role) for role in ('ff','comb','tie')}
libdir=pathlib.Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM')
clocks={}; hashes={}
for corner in ('TT','FF'):
 p=libdir/('asap7sc7p5t_SEQ_RVT_'+corner+'_nldm_220123.lib'); t=p.read_text();hashes[corner]=hashlib.sha256(p.read_bytes()).hexdigest();caps={}
 for m in ('DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'):
  c=t[t.index('cell ('+m+')'):];c=c[:c.find('\n  cell (',1)];q=c[c.index('pin (CLK)'):];q=q[:q.index('}')];caps[m]=float(re.search(r'capacitance\s*:\s*([0-9.]+)',q)[1])
 clocks[corner]=dict(masters_fF=caps,added_fF=sum((r['copies']-1)*caps[r['master']] for r in rows if r['role']=='ff'))
families=collections.Counter()
for r in rows:
 if r['role']=='ff':families[r['driver'].split('[')[0].rstrip('\\')]+=r['copies']-1
cone=set()
def visit(n):
 if n in cone or n not in by or by[n]['role']!='comb':return
 cone.add(n)
 for x in incoming[n].values():visit(x['source'])
for r in rows:
 if r['role']=='comb':visit(r['driver'])
out=dict(schema='opentallas.s81.hb1.fixedpoint.v1',scope='MODEL ONLY; graph capacity conditional on exact same-edge retained source correspondence',source_commit='ceaed19c4',source_sha256='cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3',census_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),native_odb_sha256=d['odb_sha256'],native_cells=d['cells'],native_ff=d['ff'],all_nonclock_roots=len(rs),original_over32=len(d['over32']),round_totals=rounds,added=extra,added_area_um2=sum(r['area_um2'] for r in rows),functional_added_area_um2=sum(r['area_um2'] for r in rows if r['role']!='tie'),physical_tie_added_area_um2=sum(r['area_um2'] for r in rows if r['role']=='tie'),library_sha256=hashes,clock_increment=clocks,raw_input_max=max(r['expanded_pins'] for r in inputs),inputs=inputs,ff_families=dict(families),rows=rows,classifier_cone=[dict(driver=n,master=by[n]['master'],incoming=incoming[n]) for n in sorted(cone)],endpoint_assignments=assignments,extra_data_edges=0,unqualified=['RTL retention/miter','cold/occupied reset assertion and release','actual mapped successor','reach/outline/PG/clock/parent/token dates'])
(H/'model.json').write_text(json.dumps({k:v for k,v in out.items() if k not in ('endpoint_assignments','classifier_cone')},indent=2)+'\n')
(H/'correspondence.json.gz').write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0))
print(json.dumps({k:v for k,v in out.items() if k not in ('rows','inputs','endpoint_assignments','classifier_cone','ff_families')},indent=2));print('families',json.dumps(dict(families)));print('PASS full fixedpoint/all inputs/terminal polarity; assignments',len(assignments),'classifier cone',len(cone))
# Causal graph mutant: one pass cannot claim upstream closure.
assert rounds[0]<rounds[-1]
print('REJECT one-pass lowerbound',rounds[0],'!= fixedpoint',rounds[-1])
