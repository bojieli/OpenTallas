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
bankpaths=collections.defaultdict(lambda:collections.Counter());firstcaps=collections.defaultdict(set);examples=collections.defaultdict(list);lastnames=[]
for (port,bit),net in topouts.items():
 if port!='b_tw_data_ctl_o':continue
 lf=lastff(net)
 if lf is None:continue
 lastnames.append(lf);front={lf};seen=set()
 for dep in range(1,5):
  nex=set()
  for ff in front-seen:
   seen.add(ff);d=ffs[ff]['D'];ss=support(d) if d is not None else ()
   for kind,name in ss:
    if kind=='ROM':
     bankpaths[name][dep]+=1;firstcaps[name].add(ff)
     if len(examples[name])<6:examples[name].append({'output_bit':bit,'registered_edges':dep,'first_capture':ff,'last_launch':lf})
    elif kind=='FF':nex.add(name)
  front=nex
  if not front:break
out={'source_sha':'d90b10921','metadata':str(p),'scope':'Actual mapped native JSON graph only; no placement/timing/value-activation proof','native_leaf_counts':dict(primcount),'ff_total':len(ffs),'clock_ff_counts':dict(clockcounts),'clock_examples':clockdetail,'non_single_primary_clock':unknown[:30],'non_single_primary_clock_count':len(unknown),'b_tw_data_ctl_native_last_launch_count':len(lastnames),'ROM_to_b_tw_data_ctl_registered_support_counts':{k:dict(v) for k,v in bankpaths.items()},'ROM_first_capture_cells':{k:sorted(v) for k,v in firstcaps.items()},'ROM_capture_examples':dict(examples),'warning':'Support counts may include multiple structural paths to same output bit; count is not unique bit count or programme-active payload count. No new FF/cycle is inferred or inserted.'}
(B/'native_graph.json').write_text(json.dumps(out,indent=2)+'\n')
print('CLOCKCOUNTS',dict(clockcounts));print('CLOCKUNRESOLVED',len(unknown));print('ROM_SUPPORT',{k:dict(v) for k,v in bankpaths.items()});print('FIRSTCAPTURE_COUNTS',{k:len(v) for k,v in firstcaps.items()});print('TOTAL_SECS',round(time.time()-t0,2))
assert sum(primcount.values())==209152 and len(ffs)==68857 and len(macro)==4, 'native graph disagrees with actual counted netlist'
localgroups=collections.Counter()
for n,f in ffs.items():
 if roots(f['CLK'])==frozenset(['clk']):localgroups[n.rsplit('.',1)[0]]+=1
out['local_clock_groups']=dict(localgroups)
def findchain(ff,bank,remaining,seen=frozenset()):
 if ff in seen or remaining<=0:return None
 ss=support(ffs[ff]['D']);seen=seen|{ff}
 if ('ROM',bank) in ss:return [ff,bank]
 for kind,n in sorted(ss):
  if kind=='FF':
   ch=findchain(n,bank,remaining-1,seen)
   if ch:return [ff]+ch
 return None
out['ROM_registered_chain_examples']={}
for bank,ex in examples.items():
 sample=ex[0];out['ROM_registered_chain_examples'][bank]={'native_output_bit':sample['output_bit'],'last_to_first_then_ROM':findchain(sample['last_launch'],bank,4)}
(B/'native_graph.json').write_text(json.dumps(out,indent=2)+'\n')
print('LOCAL_GROUP_HEAD',localgroups.most_common(12));print('ACTUAL_REGISTER_CHAINS',out['ROM_registered_chain_examples'])
import hashlib
out['local_clock_cells']={n:f['type'] for n,f in ffs.items() if roots(f['CLK'])==frozenset(['clk'])}
lef=(B/'native_cells.lef').read_text();sizes={z[1]:[float(z[2]),float(z[3])] for z in re.finditer(r'MACRO\s+(\S+)(?:(?!\nEND\s).)*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',lef,re.S)}
out['native_DFF_bboxes_um']={typ:sizes[typ] for typ in primcount if 'DFF' in typ}
out['metadata_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(B/'native_graph.json').write_text(json.dumps(out,indent=2)+'\n')
print('DFF_BBOXES',out['native_DFF_bboxes_um'])
out['clock_export_roots']={n:sorted(roots(net)) for (n,k),net in topouts.items() if k==0 and n.startswith('fclk_out_')}
out['ROM_clock_roots']={n:sorted(roots(v['ports']['clk'][0])) for n,v in macro.items() if 'clk' in v['ports']}
out['other_clock_only_primitive_inputs']={}
primary_clock_names={x for x in topins.values() if re.match(r'^(clk(?:_t\d+|_c\d+)?|fclk_in_\w+)$',x)}
for net,z in drivers.items():
 tag,ins,typ,pn=z
 if tag[0]!='COMB':continue
 for a in ins:
  rs=roots(a)
  if rs and set(rs)<=primary_clock_names:
   key=','.join(sorted(rs));out['other_clock_only_primitive_inputs'].setdefault(key,set()).add((tag[1],repr(a)))
out['other_clock_only_primitive_inputs']={k:len(v) for k,v in out['other_clock_only_primitive_inputs'].items()}
(B/'native_graph.json').write_text(json.dumps(out,indent=2)+'\n')
print('ROM_CLOCKS',out['ROM_clock_roots']);print('EXPORT_CLOCKS',out['clock_export_roots']);print('OTHER_CLOCK_GATE_INPUTS',out['other_clock_only_primitive_inputs'])
def streambank(n):
 if not n.startswith('u_bound.u_core.u_stream.'):return None
 s=n.split('u_stream.',1)[1].split('$_')[0]
 return re.sub(r'\[\d+\]','[*]',s)
streamweights=collections.Counter();deps=collections.defaultdict(collections.Counter);primary=collections.defaultdict(collections.Counter);pub=collections.defaultdict(collections.Counter)
for n,f in ffs.items():
 bank=streambank(n)
 if bank is None:continue
 streamweights[bank]+=1
 for kind,q in support(f['D']):
  if kind=='INPUT' and '[' in q:primary[bank][q.rsplit('[',1)[0]]+=1
  elif kind=='FF':
   other=streambank(q)
   if other and other!=bank:deps[bank][other]+=1
for (port,bit),net in topouts.items():
 if port.startswith(('fclk_','cland_')):continue
 lf=lastff(net)
 if lf is None:continue
 bank=streambank(lf)
 if bank:pub[bank][port]+=1;continue
 for kind,n in support(ffs[lf]['D']):
  if kind=='FF' and streambank(n):pub[streambank(n)][port]+=1
out['stream_native_bank_counts']=dict(streamweights)
out['stream_native_bank_dependencies']={k:dict(v) for k,v in deps.items()}
out['stream_native_primary_input_support']={k:dict(v) for k,v in primary.items()}
out['stream_native_publication_support']={k:dict(v) for k,v in pub.items()}
(B/'native_graph.json').write_text(json.dumps(out,indent=2)+'\n')
print('STREAM_BANKS',len(streamweights),'SEQUENTIAL_DEPENDENCIES',sum(len(v) for v in deps.values()));print('STREAM_DIRECT_INTERFACE',{k:v for k,v in out['stream_native_publication_support'].items() if k.startswith(('so_','sw_','se_','tw_'))})
