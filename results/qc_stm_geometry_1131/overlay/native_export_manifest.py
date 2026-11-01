import json,sys,re,pathlib,collections,functools,time
B=pathlib.Path(sys.argv[1]);p=B/'phys/slw_stm_v3/run/results/asap7/dp_slw_stm_v3/base/1_2_yosys_native_metadata.json';J=json.load(open(p));M=J['modules'];TOP='qfd_qc_slw_stm'
drivers={};ffs={};macro={};topins={};topouts={};ffclk={};primcount=collections.Counter();t0=time.time()
def expand(mn,path,bind):
 m=M[mn]
 def net(b):
  if isinstance(b,str):return ('CONST',b)
  return bind.get(b,(path,b))
 if not path:
  for n,v in m['ports'].items():
   for k,b in enumerate(v['bits']):
    if v['direction']=='input':topins[net(b)]=n if len(v['bits'])==1 else f'{n}[{k}]'
    elif v['direction']=='output':topouts[n,k]=net(b)
 for n,c in m.get('cells',{}).items():
  typ=c['type'];pn=path+'.'+n if path else n;con={k:[net(x) for x in v] for k,v in c['connections'].items()};dirs=c.get('port_directions',{})
  if typ in M and '_ASAP7_' not in typ and not typ.startswith('ot_rom_') and M[typ].get('cells'):
   mp={}
   for q,v in M[typ].get('ports',{}).items():
    if q not in con:continue
    for a,b in zip(v['bits'],con[q]):mp[a]=b
   expand(typ,pn,mp);continue
  primcount[typ]+=1
  ins=tuple(x for k,v in con.items() if dirs.get(k)=='input' for x in v)
  if 'DFF' in typ:
   ck=con.get('CLK',con.get('CK',[]));d=con.get('D',[]);ffs[pn]={'type':typ,'D':d[0] if d else None,'CLK':ck[0] if ck else None};tag=('FF',pn)
  elif typ.startswith('ot_rom_'):
   macro[pn]={'type':typ,'ports':con};tag=('ROM',pn)
  else:tag=('COMB',pn)
  for q,v in con.items():
   if dirs.get(q)=='output':
    for b in v:drivers[b]=(tag,ins,typ,q)
expand(TOP,'',{})
print('FLATTEN',sum(primcount.values()),'FF',len(ffs),'ROM',len(macro),'secs',round(time.time()-t0,2),flush=True)
@functools.lru_cache(None)
def roots(n):
 if n in topins:return frozenset([topins[n]])
 if n[0]=='CONST':return frozenset()
 z=drivers.get(n)
 if not z:return frozenset(['UNDRIVEN'])
 tag,ins,typ,pn=z
 if tag[0]=='FF':return frozenset(['STATE'])
 if tag[0]=='ROM':return frozenset(['ROM'])
 return frozenset().union(*(roots(x) for x in ins))
clockcounts=collections.Counter();clockdetail={};unknown=[]
for n,f in ffs.items():
 rs=roots(f['CLK']) if f['CLK'] is not None else frozenset(['NOCLK'])
 ck=sorted(x for x in rs if re.match(r'^(clk(?:_t\d+|_c\d+)?|fclk_in_\w+)$',x))
 key=','.join(ck) if ck else 'NO_PRIMARY_CLOCK';clockcounts[key]+=1
 if key not in clockdetail:clockdetail[key]={'example':n,'other_roots':sorted(set(rs)-set(ck))}
 if len(ck)!=1:unknown.append({'cell':n,'roots':sorted(rs)})
# Stop combinational support at state or ROM outputs. This is structural support, no equivalence/activation claim.
@functools.lru_cache(None)
def support(n):
 if n in topins:return frozenset([('INPUT',topins[n])])
 if n[0]=='CONST':return frozenset()
 z=drivers.get(n)
 if not z:return frozenset([('UNDRIVEN',repr(n))])
 tag,ins,typ,pn=z
 if tag[0] in ('FF','ROM'):return frozenset([tag])
 return frozenset().union(*(support(x) for x in ins))
def lastff(n):
 seen=set()
 while n not in seen:
  seen.add(n);z=drivers.get(n)
  if not z:return None
  tag,ins,typ,pn=z
  if tag[0]=='FF':return tag[1]
  if re.match(r'^(BUF|INV|HB)',typ) and len(ins)==1:n=ins[0];continue
  return None

T=json.load(open(B/'source_type.json'));out=[]
for p in T['clock']['landing_contract']['pins']:
 if 'source_clock_tap' not in p:continue
 name=p['name'].removeprefix('fclk_out_');rows=[];counts=collections.Counter()
 for (port,bit),net in topouts.items():
  if port!=name:continue
  lf=lastff(net)
  rr=sorted(roots(ffs[lf]['CLK'])) if lf else sorted(roots(net))
  counts[','.join(rr)]+=1
  rows.append({'bit':bit,'last_native_launch_FF':lf,'actual_native_clock_roots':rr})
 out.append({'data_port':name,'export_port':p['name'],'source_clock_port':p['source_clock_port'],'declared_source_clock_tap':p['source_clock_tap'],'actual_native_launch_root_counts':dict(counts),'bits':rows,'qualification':'PRE_PHYSICAL_NATIVE_GRAPH only; explicit tap geometry does not prove post-hook identity'})
res={'source':'d90b109213c6949da87b330ef143d96bbe937934','native_leaves':sum(primcount.values()),'exports':out,'ROM_clocks':{n:sorted(roots(next(bs[0] for pn,bs in v['ports'].items() if pn.lower() in ('clk','ck','clock')))) for n,v in macro.items()},'note':'source_clock_port remains authoritative current export Tcl input; source_clock_tap tags retained, not silently reassigned by estimated consumer clusters.'}
(B/'native_export_launch_manifest.json').write_text(json.dumps(res,indent=1)+'\n')
for x in out:print(x['data_port'],len(x['bits']),x['declared_source_clock_tap'],x['actual_native_launch_root_counts'])
