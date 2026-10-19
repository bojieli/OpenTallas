import importlib.util,json,pathlib,collections,hashlib
r=pathlib.Path('.');sp=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
p=r/'synth_fork_r2/results/asap7/opentallas_qkd_kvs_attn_safe_control_asap7_ref_gate/base/1_2_yosys.v';g,top=T.flatten(T.parse_verilog(p.read_text()),None);A=T.build(g,None);clock={x for n,(d,x) in g.ports.items() if n=='ck'};rows=[]
for x,ls in A['loads'].items():
 if x<4 or x in clock:continue
 ci,pn=A['driver'].get(x,(-2,'UNDRIVEN'));assert ci!=-2;ends=set();seen=set();stack=[x]
 while stack:
  y=stack.pop()
  if y in seen:continue
  seen.add(y)
  for li,lp,bit in A['loads'].get(y,[]):
   if A['kind'][li]=='buf':stack.extend(v for op,bs in g.cells[li][2].items() if A['pin_dir'][li][op]=='out' for v in bs)
   else:ends.add((li,lp,bit))
 rows.append({'net':g.net_name[x],'driver':ci,'kind':A['kind'][ci] if ci>=0 else 'port','loads':len(ls),'first_logic':len(ends)})
rawbad=[r for r in rows if r['loads']>32];firstbad=[r for r in rows if r['kind']!='buf' and r['first_logic']>32]
result={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'top':top,'cells':len(g.cells),'FF':sum(k=='ff' for k in A['kind']),'direct_max':max(r['loads'] for r in rows),'first_logic_max':max(r['first_logic'] for r in rows if r['kind']!='buf'),'input_max':max(r['loads'] for r in rows if r['kind']=='port'),'raw_bad':rawbad,'first_bad':firstbad,'clock_loads':sum(len(A['loads'][x]) for x in clock),'kind':dict(collections.Counter(A['kind'])),'rows':rows,'native_timing_qualified':False}
(r/'candidate/post_synth.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}));assert not rawbad and not firstbad;assert result['FF']==6040,'unexpected register insertion/removal'
