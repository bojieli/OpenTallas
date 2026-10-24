from pathlib import Path
import re,json,sys
from collections import Counter
base=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src')
sys.path.insert(0,'/home/ubuntu/wt/tokd-hbm2-tools/tools/hbm_die_v16')
import d4g_bank_latency as L
I=json.loads((base/'contract_func.json').read_text())['instances']
G=L.Graph.__new__(L.Graph);G.I=I
want={('hb_coll_SW','pr_cw_i'),('hb_coll_SW','pr_ccw_i'),('hcollb_SW','cw_i'),('hcollb_SW','ccw_i'),('hcollgi_SW','launch_v'),('hcollgi_SW','desc_v'),('calendar_SW','launch_v')}
inst={};cur=None;buf=[]
for line in (base/'die.v').open():
 if cur is None:
  m=re.match(r'\s*(\w+)\s*(?:#\(.*?\))?\s+(\w+)\s*\(\s*$',line)
  if m and (re.match(r'(rf|rh)\d+_|l12p_',m[2]) or m[2] in {w[0] for w in want}):cur=m.groups();buf=[]
 elif re.match(r'\s*\);',line):inst[cur[1]]=(cur[0],dict(re.findall(r'\.(\w+)\((.*?)\)\s*,?\s*$', ''.join(buf),re.M)));cur=None
 else:buf.append(line)
out={}
for name,port in sorted(want):
 expr=inst[name][1][port];hops=[];seen=set()
 while True:
  m=re.search(r'\b((?:rf|rh)\d+_\w+?|l12p_\w+?)__(o|b|eb|ck_o)\b',expr)
  if not m or m[1] not in inst:break
  h=m[1];assert h not in seen;seen.add(h);hops.append(h);_,pp=inst[h];expr=pp.get('i') or pp.get('a') or ''
 lat,notes=G.lane_latency(hops[::-1]);out[name+'.'+port]=dict(source_root=expr,wrappers=len(hops),latency_edges=lat,notes=notes,source_to_sink_hops=hops[::-1])
print(json.dumps(out,indent=2))
