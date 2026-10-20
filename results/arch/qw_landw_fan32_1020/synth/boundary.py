import json,pathlib,collections
r=pathlib.Path.cwd()
for label in ['landw107final','landw116final','landwn107final','landwn116final']:
 d=r/'native_synth_out'/label/'work/orfs';j=json.loads((d/'flat.json').read_text());m=next(v for v in j['modules'].values()if 'a'in v.get('ports',{})and 'ck_s'in v['ports']);c=m['cells'];sinks=collections.defaultdict(list)
 for n,v in c.items():
  for pn,bits in v['connections'].items():
   if v['port_directions'][pn]=='input':
    for b in bits:sinks[b].append((n,pn))
 rows=[]
 for idx,b in enumerate(m['ports']['a']['bits']):
  todo=[(b,[])];seen=set()
  while todo:
   net,path=todo.pop()
   if net in seen:continue
   seen.add(net)
   for n,pn in sinks[net]:
    v=c[n];entry=dict(cell=n,type=v['type'],pin=pn)
    if 'DFF'in v['type']:
     rows.append(dict(input_bit=idx,first_ff=entry,path=path,clock_pins={k:bs for k,bs in v['connections'].items()if k.upper()in ['CLK','CK','CP','CLKN']}));continue
    assert pn not in ['CLK','CK','CP'],(n,pn)
    assert len(path)<4,(n,path)
    for op,bs in v['connections'].items():
     if v['port_directions'][op]=='output':
      for ob in bs:todo.append((ob,path+[entry]))
 counts=collections.Counter(tuple(v['type']for v in x['path'])for x in rows)
 o=dict(top=m.get('attributes',{}).get('top'),input_count=len(m['ports']['a']['bits']),first_storage_paths=len(rows),max_logic_cells=max(len(x['path'])for x in rows),gate_role_paths=[dict(types=list(k),count=v)for k,v in counts.items()],examples=rows[:12],all_first_ff_names=sorted(set(x['first_ff']['cell']for x in rows)))
 (d/'input_boundary.json').write_text(json.dumps(o,indent=2)+'\n');print(label,o['input_count'],o['first_storage_paths'],o['gate_role_paths'],flush=True)
