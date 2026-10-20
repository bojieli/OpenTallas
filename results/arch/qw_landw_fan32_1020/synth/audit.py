import pathlib,json,collections,re,hashlib,os
p=pathlib.Path('flat.json');m=json.loads(p.read_text())['modules'][os.environ.get('OT_NATIVE_TOP','qfd_landh0d8f_116_EW_54x54')];cells=m['cells'];constant_cells=json.loads(pathlib.Path('lib_roles.json').read_text())['actual_literal_constant_cells'];inputs=collections.defaultdict(list);ports=collections.defaultdict(list)
def trans(c):return bool(re.match(r'^(BUF|INV|HB)[x0-9_]',c['type'],re.I))
def clockpin(n):return n.upper()in['CLK','CK','CP','GCLK','CLKN','CLKB']
for n,c in cells.items():
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]=='input'and not clockpin(pn)and pn not in['VDD','VSS','VPWR','VGND']:
   for b in bs:
    if isinstance(b,int):inputs[b].append((n,pn))
for n,v in m['ports'].items():
 if v['direction']=='output':
  for b in v['bits']:
   if isinstance(b,int):ports[b].append(n)
def census(root):
 todo=[root];seen=set();sinks=set()
 while todo:
  b=todo.pop()
  if b in seen:continue
  seen.add(b);sinks.update('port:'+n for n in ports[b])
  for n,pn in inputs[b]:
   c=cells[n]
   if trans(c):todo.extend(x for on,bs in c['connections'].items()if c['port_directions'][on]=='output'for x in bs if isinstance(x,int))
   else:sinks.add(n+'/'+pn)
 return len(sinks),sorted(sinks)[:6]
rows=[]
for n,c in cells.items():
 if trans(c):continue
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]!='output':continue
  for b in bs:
   if isinstance(b,int):
    loads,ex=census(b);rows.append(dict(root=n+'/'+pn,kind='tie'if c['type']in constant_cells else'ff'if'DFF'in c['type']else'comb',loads=loads,examples=ex))
for n,v in m['ports'].items():
 if v['direction']=='input'and n not in['ck','ck_s']:
  for i,b in enumerate(v['bits']):
   if isinstance(b,int):
    loads,ex=census(b);rows.append(dict(root='input:'+n+'['+str(i)+']',kind='input',loads=loads,examples=ex))
rows.sort(key=lambda x:-x['loads']);bad=[x for x in rows if x['kind']!='tie'and x['loads']>32];const={n:v['bits']for n,v in m['ports'].items()if v['direction']=='output'and n not in['tie_hi','tie_lo']and any(isinstance(x,str)for x in v['bits'])};out=dict(flat_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cells=len(cells),ff=sum('DFF'in c['type']for c in cells.values()),roots=len(rows),over32_non_tie=len(bad),max_non_tie=max(x['loads']for x in rows if x['kind']!='tie'),violations=bad,constant_functional_outputs=const,actual_literal_constant_cells=constant_cells,raw_constant_roots=[x for x in rows if x['kind']=='tie'],top=rows[:40]);pathlib.Path('native32.json').write_text(json.dumps(out,indent=2)+'\n');pathlib.Path('all_roots.json').write_text(json.dumps(rows,indent=2)+'\n');print('NATIVE32',out['over32_non_tie'],'max',out['max_non_tie'],'FF',out['ff'])
