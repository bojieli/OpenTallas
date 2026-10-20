"""Recover actual reread FF correspondence from surviving published source wire aliases."""
import json,pathlib,sys,re
r=json.loads(pathlib.Path(sys.argv[1]).read_text());actual=json.loads(pathlib.Path(sys.argv[2]).read_text())['modules']['qfd_sys_face_record_port_n32'];orig=json.loads(pathlib.Path(sys.argv[3]).read_text())['modules']['qfd_sys_face_record_port'];mapping={};nxt=max(b for c in orig['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
for pn,p in actual['ports'].items():
 if pn in ['source_copies','rst_leaf'] or p['direction']!='input':continue
 assert len(p['bits'])==len(orig['ports'][pn]['bits'])
 for ab,ob in zip(p['bits'],orig['ports'][pn]['bits']):mapping[ab]=ob
for c in actual['cells'].values():
 for bs in c['connections'].values():
  for b in bs:
   if isinstance(b,int) and b not in mapping:mapping[b]=nxt;nxt+=1
for p in actual['ports'].values():
 for b in p['bits']:
  if isinstance(b,int) and b not in mapping:mapping[b]=nxt;nxt+=1
expected={c['connections']['Q'][0]:r['origins'][n] for n,c in r['graph']['cells'].items() if c['type'].startswith('$_DFF')}
aliases={}
for n,v in actual['netnames'].items():
 mt=re.fullmatch(r'n_(\d+)',n)
 if mt and int(mt[1]) in expected:
  assert len(v['bits'])==1;aliases.setdefault(v['bits'][0],set()).add(expected[int(mt[1])])
origins={}
for n,c in actual['cells'].items():
 if c['type'].startswith('$_DFF'):
  targets=aliases.get(c['connections']['Q'][0],set());assert len(targets)==1,(n,targets);origins[n]=next(iter(targets))
assert origins,'actual source was not fully flattened; no state correspondence'
cp=[dict(x,copy_bit=mapping[actual['ports']['source_copies']['bits'][x['index']]]) for x in r['input_copies']]
leaves=[dict(x,bit=mapping[actual['ports']['rst_leaf']['bits'][x['index']]]) for x in r['reset_leaves']]
for c in actual['cells'].values():c['connections']={p:[mapping[b] if isinstance(b,int) else b for b in bs] for p,bs in c['connections'].items()}
for p in actual['ports'].values():p['bits']=[mapping[b] if isinstance(b,int) else b for b in p['bits']]
r.update(graph=actual,origins=origins,input_copies=cp,reset_leaves=leaves)
pathlib.Path(sys.argv[4]).write_text(json.dumps(r)+'\n');print('Actual reread FFs',len(origins),'all have unique original FF correspondence')
