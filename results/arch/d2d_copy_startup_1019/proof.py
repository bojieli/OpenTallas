import json,random,hashlib
from pathlib import Path
j=json.loads(Path('cone.json').read_text());rng=random.Random(1019)
def gate(t,p):
 t=t.split('x')[0]
 if t=='BUF':return p['A']
 if t=='INV':return not p['A']
 if t.startswith(('AND','NAND','OR','NOR')):
  f=all(p.values()) if 'AND' in t else any(p.values())
  return not f if t.startswith('N') else f
 if t in ['AO21','AOI21']:r=(p['A1'] and p['A2']) or p['B'];return not r if t=='AOI21' else r
 if t=='OA211':return (p['A1'] or p['A2']) and p['B'] and p['C']
 if t=='OA22':return (p['A1'] or p['A2']) and (p['B1'] or p['B2'])
 raise ValueError(t)
def evaluate(v,clone):
 cache={}
 def ev(n):
  if n in cache:return cache[n]
  if n in v:return v[n]
  name,t,pins=j['cells'][n];p={k:ev(ns[0]) for k,ns in pins.items() if k not in ['Y','Z','QN']}
  if clone and name==j['target']:p[j['replace_pin']]=not v[j['original_net']]
  r=bool(gate(t,p));cache[n]=r;return r
 r=ev(j['root']);return r,cache
for trial in range(10000):
 v={n:bool(rng.getrandbits(1)) for n in j['leaves']}
 for n,d in j['leaves'].items():
  if d and d[1].startswith('TIE'):v[n]=d[2] in ['H','Y'] and 'HI' in d[1]
 a,ca=evaluate(v,False);b,cb=evaluate(v,True)
 if a!=b:
  result={'verdict':'FAIL_FIRST_CONSUMER_EDGE','trial':trial,'leaf_values':{k:int(x) for k,x in v.items()},'original_qn_before_edge':int(v[j['original_net']]),'clone_qn_before_edge':int(not v[j['original_net']]),'sink_resetn':1,'sink_setn':1,'original_sink_D':int(a),'clone_sink_D':int(b),'original_sink_QN_after_first_edge':int(not a),'clone_sink_QN_after_first_edge':int(not b),'note':'Four unreset clone FF outputs are unconstrained at startup. The parent and clone capture the same D on this edge, but txcal consumer samples old QN through this exact cone. All other FF QNs, input bits and macro outputs are identical in both worlds.','cone_sha256':hashlib.sha256(Path('cone.json').read_bytes()).hexdigest()};Path('witness.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));break
else:raise SystemExit('No witness found: inconclusive')
