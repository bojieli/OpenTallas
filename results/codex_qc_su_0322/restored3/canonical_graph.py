import json,re,hashlib,pathlib,collections
P=pathlib.Path(__file__).resolve().parent/'current_packet'
def vec(e,W):
 e=e.strip()
 if e.startswith('{') and e.endswith('}'):
  assert '{' not in e[1:-1];out=[]
  for v in reversed(e[1:-1].split(',')):out+=vec(v,W)
  return out
 m=re.fullmatch(r"(\d+)'([bdh])([0-9a-fxz]+)",e,re.I)
 if m:
  n=int(m[1]);base={'b':2,'d':10,'h':16}[m[2].lower()];s=m[3].lower();assert 'x' not in s and 'z' not in s;v=int(s,base);return [('CONST',(v>>j)&1) for j in range(n)]
 m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',e);assert m,e
 if m[2] is None:return [(m[1],j) for j in range(W[m[1]])]
 hi=int(m[2]);lo=int(m[3]) if m[3] else hi;assert hi>=lo
 return [(m[1],j) for j in range(lo,hi+1)]
def canonical(m):
 r=json.load(open(P/'cuts'/m/'cut.json'));s=(P/'rtl'/(m+'.sv')).read_text();W={n:int(w)+1 if w else 1 for w,n in re.findall(r'wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*;',s)};W.update(clk=1,rst_n=1)
 ins={(z['name'],z['bit']):i for i,z in enumerate(r['inputs'])};outs={(z['name'],z['bit']):i for i,z in enumerate(r['outputs'])}
 def b(q):
  if q[0]=='CONST':return list(q)
  if q[0]=='clk':return ['CLK',0]
  if q[0]=='rst_n':return ['RST',0]
  if q in ins:return ['I',ins[q]]
  if q in outs:return ['O',outs[q]]
  n=re.sub(r'(?<=exp)\d+|(?<=rsq)\d+|(?<=head)\d+|(?<=rcp)\d+|(?<=lrly)\d+','LANE',q[0]);return [n,q[1]]
 cells=[]
 for match in re.finditer(r'^    (\w+)(?: (#[^\n]*))? (u_u_(exp|rsq|head|rcp|lrly)\d+) \(\n(.*?)^    \);',s,re.M|re.S):
  mod,params,inst,kind,ports=match.groups();pp={}
  for name,e in re.findall(r'\.(\w+)\(([^()]+)\)',ports):pp[name]=[b(q) for q in vec(e,W)]
  cells.append(dict(role=kind,module=mod,params=re.sub(r'\s+','',params or ''),ports=pp))
 assert len(cells)==5,(m,len(cells));cells.sort(key=lambda x:x['role']);z=dict(inputs=r['input_bits'],outputs=r['output_bits'],cells=cells);return z
def census():
 rows=[];groups=collections.defaultdict(list)
 for m in sorted(p.name for p in (P/'cuts').iterdir()):
  z=canonical(m);h=hashlib.sha256(json.dumps(z,sort_keys=True).encode()).hexdigest();groups[h].append(m);rows.append(dict(module=m,canonical_graph_sha256=h))
 return dict(scope='Exact five-leaf port-bit graph with named nets alpha-renamed and actual boundary bits fixed; no arithmetic/reset/parameter changes',groups=dict(groups),rows=rows)
if __name__=='__main__':
 x=census();print(json.dumps(x,indent=1));(P.parent/'canonical_graphs.json').write_text(json.dumps(x,indent=1)+'\n')
