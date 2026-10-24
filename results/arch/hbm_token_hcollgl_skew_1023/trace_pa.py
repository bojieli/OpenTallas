from pathlib import Path
import re,json,sys
base=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src')
sys.path.insert(0,'/home/ubuntu/wt/tokd-hbm2-tools/tools/hbm_die_v16')
import d4g_bank_latency as L
I=json.loads((base/'contract_func.json').read_text())['instances']
G=L.Graph.__new__(L.Graph);G.I=I
want=[(f'hcollrs_{q}',p) for q in ('SW','NW','NE','SE') for p in ('a_rq','b_rq','vm_rr')]
inst={};cur=None;buf=[]
for line in (base/'die.v').open():
 if cur is None:
  m=re.match(r'\s*(\w+)\s*(?:#\(.*?\))?\s+(\w+)\s*\(\s*$',line)
  if m and (re.match(r'(rf|rh)\d+_|l12p_',m[2]) or m[2] in {w[0] for w in want}):cur=m.groups();buf=[]
 elif re.match(r'\s*\);',line):inst[cur[1]]=(cur[0],dict(re.findall(r'\.(\w+)\((.*?)\)\s*,?\s*$', ''.join(buf),re.M)));cur=None
 else:buf.append(line)
out={}
for name,port in want:
 expr=inst[name][1][port];hops=[];seen=set()
 while True:
  m=re.search(r'\b((?:rf|rh)\d+_\w+?|l12p_\w+?)__(o|b|eb|ck_o)\b',expr)
  if not m or m[1] not in inst:break
  h=m[1];assert h not in seen;seen.add(h);hops.append(h);_,pp=inst[h];expr=pp.get('i') or pp.get('a') or ''
 try: lat,notes=G.lane_latency(hops[::-1])
 except Exception as e: lat,notes=None,str(e)
 out[name+'.'+port]=dict(source_root=expr,wrappers=len(hops),latency_edges=lat,notes=notes,hops=hops[::-1],types=[inst[h][0] for h in hops[::-1]])
print(json.dumps(out,indent=1))
