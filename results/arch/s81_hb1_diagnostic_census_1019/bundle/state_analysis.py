import collections,json,gzip,pathlib,re,hashlib
O=pathlib.Path('/work');d=json.load(open(O/'mapped.json'));top=d['modules']['ot_s81sl_xr3'];native=json.load(gzip.open(O/'native_census.json.gz','rt'))
ff={n:c for n,c in top['cells'].items() if c['type'].startswith('DFF')}
unescape=lambda n:n.replace('\\[','[').replace('\\]',']')
native_outputs={(unescape(r['driver']),r['pin']) for r in native['records'] if r['role']=='ff'}
assert {n for n,p in native_outputs}==set(ff), 'native vs mapped FF identity mismatch'
bitowners={bit:(n,p) for n,c in ff.items() for p,bs in c['connections'].items() if (n,p) in native_outputs for bit in bs}
# Source wire may be after INV because ASAP7 HQN polarity is inverted.
transparent={}; ties={}
pin_roles={(unescape(x['instance']),x['pin']):x['direction'] for x in native['pin_inventory']}
for n,c in top['cells'].items():
 if c['type'].startswith(('BUF','INV','HB')):
  ins=[b for p,bs in c['connections'].items() if pin_roles.get((n,p))=='INPUT' for b in bs]
  outs=[b for p,bs in c['connections'].items() if pin_roles.get((n,p))=='OUTPUT' for b in bs]
  assert len(ins)==len(outs)==1,(n,ins,outs)
  transparent[outs[0]]=ins[0]
 if c['type'].startswith('TIE'):
  for p,bs in c['connections'].items():
   if pin_roles.get((n,p))=='OUTPUT':
    for bit in bs:ties[bit]='1' if c['type'].startswith('TIEHI') else '0'
import functools
@functools.lru_cache(None)
def resolve(bit):
 if bit in bitowners:return bitowners[bit]
 if bit in transparent:return resolve(transparent[bit])
 return None
state=[]
for n,w in sorted(top['netnames'].items()):
 owners=sorted({resolve(x)[0] for x in w['bits'] if resolve(x)});constants=collections.Counter(ties.get(x,str(x)) for x in w['bits'] if isinstance(x,str) or x in ties)
 if owners or constants:state.append(dict(name=n,width=len(w['bits']),ff_outputs=len(owners),ff_cells=owners,constants=dict(constants),attributes=w.get('attributes',{})))
roles={}
for r,pat in {'band_capture':r'(^|[.])bb(?:$|\[)', 'band_output':r'(^|[.])(bo_r|bo)(?:$|\[)', 'packet_holding':r'(^|[.])ud\[', 'packet_context':r'(^|[.])(ub|un\[|ul\[|ur\[)', 'packet_assembly':r'(^|[.])(pk|pn|pk_go)(?:$|\[|\$)', 'landing_reset':r'__ot_rl', 'region_reset':r'u_rr', 'input_capture':r'(^|[.])(eb|wb|vb|bb|ev|wv|vv|sid_c|lov|pv|lod|pd|rbd)(?:$|\[|\$)'}.items():
 rows=[s for s in state if re.search(pat,s['name'])];direct={n for n in ff if re.search(pat,n)};roles[r]=dict(pattern=pat,nets=[s['name'] for s in rows],unique_ff_cells=sorted(direct|{x for s in rows for x in s['ff_cells']}),constant_bits=sum(sum(s['constants'].values()) for s in rows))
def blocks(txt,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(\s*([^)]*?)\s*\)\s*\{',txt):
  k=m.end();depth=1;j=k
  while depth:
   depth+=(txt[j]=='{')-(txt[j]=='}');j+=1
  yield m.group(1).strip('"'),txt[k:j-1]
clock={}
for corner in ('TT','FF','SS'):
 p=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_'+corner+'_nldm_220123.lib');text=p.read_text();cells={}
 for name,body in blocks(text,'cell'):
  if name not in native['master_counts']:continue
  for pin,pbody in blocks(body,'pin'):
   if not re.search(r'clock\s*:\s*true',pbody):continue
   cap=float(re.search(r'(?m)^\s*capacitance\s*:\s*([0-9.eE+-]+)',pbody).group(1));cells[name]=dict(pin=pin,capacitance=cap,count=native['master_counts'][name])
 clock[corner]=dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),capacitance_unit=re.search(r'capacitive_load_unit\s*\(([^)]*)',text).group(1),masters=cells,total=sum(x['capacitance']*x['count'] for x in cells.values()))
summary=dict(mapped_cells=len(top['cells']),mapped_ff=len(ff),roles={k:{**v,'unique_ff_count':len(v['unique_ff_cells'])} for k,v in roles.items()},clock=clock,constant_net_count=sum(bool(s['constants']) for s in state),native_vs_mapped_count_equal=len(top['cells'])==native['cells'],full_source_attribution='Native transparent-chain resolved aliases in mapped.json plus ORFS canonical RTLIL; alias state ledger is not an equivalence/lifetime proof')
json.dump(summary,open(O/'state_summary.json','w'),indent=2)
with gzip.open(O/'state_ledger.json.gz','wt') as f:json.dump(state,f,separators=(',',':'))
print(json.dumps({k:v for k,v in summary.items() if k!='roles'}));print({k:v['unique_ff_count'] for k,v in summary['roles'].items()})
