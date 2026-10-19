import re,json,pathlib,hashlib
A=pathlib.Path('/home/ubuntu/artifacts/kv-token-authority-source-1019'); root=A/'receipt/g7/files/srv/opentallas-scratch/claude/kv-tok/veh/g7/WSQK/cut'; s=(root/'qwk_stk_WS.sv').read_text()
width={n:int(h)+1 for h,n in re.findall(r'(?:wire|input wire|output wire)\s+\[(\d+):0\]\s+(\w+)',s)}
def bits(e):
 e=e.strip()
 if e.startswith('{'):return sum([bits(x) for x in e[1:-1].split(',')],[])
 m=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',e)
 if m:
  n,h,l=m.groups();return [(n,i) for i in range(int(h),int(l if l is not None else h)-1,-1)]
 if re.fullmatch(r"\d+'[bdh][0-9a-fA-F]+",e):return [('CONST',e)]*int(e.split("'")[0])
 return [(e,i) for i in range(width.get(e,1)-1,-1,-1)]
dr={}; inst={}
for ln,l in enumerate(s.splitlines(),1):
 m=re.match(r'\s*(\w+)\s+(?:#\(.*\)\s+)?(\w+)\s+\((.*)\);',l)
 if not m:continue
 typ,n,body=m.groups(); ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',body));inst[n]={'type':typ,'ports':ports,'line':ln}
 if typ.startswith(('qkd_rlys','qkd_rlysh','qkd_landsh')) and 'a' in ports and 'b' in ports:
  aa,bb=bits(ports['a']),bits(ports['b']);assert len(aa)==len(bb),(n,len(aa),len(bb))
  for a,b in zip(aa,bb):
   assert b not in dr, ('multiple relay drivers',b)
   dr[b]={'a':a,'name':n,'type':typ,'clock':ports.get('ck',ports.get('ic','UNKNOWN')),'line':ln}
for ln,l in enumerate(s.splitlines(),1):
 m=re.match(r'\s*assign (\w+(?:\[\d+:\d+\])?) = ([^;]+);',l)
 if m:
  for b,a in zip(bits(m[1]),bits(m[2])):dr[b]={'a':a,'name':'assign','type':'assign','line':ln}
def trace(n,b=0):
 cur=(n,b);out=[]
 while cur in dr:
  d=dr[cur];out.append(dict(d,out=cur));cur=tuple(d['a']);assert len(out)<200
 return {'end':cur,'registered_edges':sum(x['type']!='assign' for x in out),'path':out}
mp=(root/'kva_grp_map.svh').read_text();names=['n_ks_kvs_attn__attn__tx_valid__r6__beq3','n_ks_prg__r3__pinfix1']
names += re.findall(r'assign kva_[kv]req\[\d+\] = o_(\w+);',mp)
r={n:trace(n) for n in names}
# Also reset ancestry for each real producer landing.
selected={k:v for k,v in inst.items() if k=='kvs_attn' or k.startswith('ectl_WS_') or v['type']=='qkd_pv16_vport_b'}
for k,v in selected.items():
 if 'rst_n' in v['ports']:v['reset_trace']=trace(*bits(v['ports']['rst_n'])[0])
(A/'frontiers.json').write_text(json.dumps({'cut_sha256':hashlib.sha256(s.encode()).hexdigest(),'valid_paths':r,'producers':selected},indent=2))
assert len(r)==18
assert [x['registered_edges'] for n,x in r.items() if n.startswith('n_krq_')]==[69,69,67,63,56,47,34,51]
assert [x['registered_edges'] for n,x in r.items() if n.startswith('n_pvvq_')]==[6,4,6,4,6,4,6,4]
assert r[names[0]]['registered_edges']==9 and r[names[1]]['registered_edges']==5
assert all(x['type']=='qkd_rlys_1' or x['type']=='qkd_rlys_36' or x['type']=='assign' or x['type']=='qkd_rlys_528' for v in r.values() for x in v['path'])
for n,t in r.items():print(n,t['registered_edges'],t['end'],sorted(set(x.get('clock','') for x in t['path'])))
for k,v in selected.items():print(k,v['type'],v['ports'].get('rst_n'),v.get('reset_trace',{}).get('registered_edges'),v.get('reset_trace',{}).get('end'))
