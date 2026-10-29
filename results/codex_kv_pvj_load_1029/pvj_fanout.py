import re,json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pvj-load-1029');k=p/'kits/ot_qwen_tp8_pv_join_t__172.8x172.8'
s=(k/'1_synth_odb.v').read_text();cells=re.findall(r'^\s*(\w+_ASAP7_\w+)\s+(\\\S+|\w+)\s+\((.*?)\);',s,re.M|re.S)
loads={};ff=[]
for m,n,ports in cells:
 for pin,net in re.findall(r'\.(\w+)\(([^()]*)\)',ports):
  net=net.strip()
  if pin not in ['Q','QN','Y','Z']:loads.setdefault(net,[]).append(n+'/'+pin)
 if 'DFF' in m and 'g_output_load_local' in n:
  q=re.search(r'\.Q(?:N)?\(([^()]*)\)',ports).group(1).strip();ff.append((n,q))
out={n:dict(q=q,load=len(loads.get(q,[])),examples=loads.get(q,[])[:3])for n,q in ff}
(p/'mapped_local_fanout.json').write_text(json.dumps(out,indent=1)+'\n');print('ACTUAL_LOCAL_FANOUT',[(re.search(r'word\[(\d+)\]',n)[1],v['load'])for n,v in out.items()]);print('cells',len(cells))
byname={n:(m,dict(re.findall(r'\.(\w+)\(([^()]*)\)',ports)))for m,n,ports in cells}
def leaves(net,seen=None):
 seen=set() if seen is None else seen
 assert net not in seen,'cycle';seen=seen|{net};ans=[]
 for ep in loads.get(net,[]):
  n,pin=ep.rsplit('/',1);m,pp=byname[n]
  if m.startswith(('BUF','INV')):
   outnet=pp.get('Y',pp.get('Z','')).strip();assert outnet,(n,m,pp)
   ans+=leaves(outnet,seen)
  else:ans.append(ep)
 return ans
for n,v in out.items():v['buffer_tree_leaves']=leaves(v['q']);v['buffer_tree_load']=len(v['buffer_tree_leaves'])
(p/'mapped_local_fanout.json').write_text(json.dumps(out,indent=1)+'\n');print('LOCAL_BUFFER_TREE_LOADS',sorted(set(v['buffer_tree_load'] for v in out.values())))
