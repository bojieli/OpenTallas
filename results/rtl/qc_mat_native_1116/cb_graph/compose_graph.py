from pathlib import Path
import re,json
S=Path(__file__).parent
text=(S/'qfd_c_b16_dv_fabric.sv').read_text();s=re.sub(r'//[^\n]*','',text)
pat=re.compile(r'\b(qfd_c_stn51[46]|qfd_c_xstnw?|qfd_q3h_stn|qfd_q3h_run|qfd_c_land_[wr])\s*(?:#\s*\((.*?)\))?\s+(\w+)\s*\((.*?)\)\s*;',re.S)
inst=[];edges={};bank={}
def edge(dst,src,w,why):
 if dst in edges:raise ValueError(('duplicate',dst))
 edges[dst]=(src,w,why)
for m in pat.finditer(s):
 mod,pa,name,body=m.groups();ports=dict(re.findall(r'\.(\w+)\s*\(([^()]*)\)',body));pars=dict(re.findall(r'\.(\w+)\s*\(([^()]*)\)',pa or ''));inst.append((mod,name,ports,pars))
 if mod=='qfd_c_land_w':bank[ports['bank']]=(ports['i'],name)
for mod,name,p,pa in inst:
 if mod in ['qfd_c_stn514','qfd_c_stn516','qfd_q3h_stn']:edge(p['q'],p['d'],int(pa.get('N','1')),name)
 elif mod=='qfd_q3h_run':edge(p['q'],p['d'],int(pa.get('D','0').rsplit(':',1)[-1].strip()),name)
 elif mod.startswith('qfd_c_xstn'):
  edge(p['a_d'],p['b_d'],1,name+':corridor');edge(p['tap_d'],p['b_d'],1,name+':GOtap')
 elif mod=='qfd_c_land_r':
  src,wr=bank[p['bank']];edge(p['o'],src,int(pa.get('K','2').rsplit(':',1)[-1].strip())+1,wr+'+'+name)
for dst,expr in re.findall(r'\b(?:assign|wire(?:\s+\[[^]]+\])?)\s+(\w+)\s*=\s*(.*?);',s,re.S):
 expr=expr.strip()
 if expr.startswith('(MUT =='):
  expr=expr.rsplit(':',1)[-1].strip().rstrip(')').strip()
 if re.fullmatch(r'\w+',expr):edge(dst,expr,0,'assign')
seed={f'bc{i}':0 for i in range(4)}
def get(n,seed,trail=()):
 if n in seed:return seed[n]
 if n in trail:raise ValueError(('loop',n,trail))
 if n not in edges:raise KeyError(n)
 src,w,why=edges[n];return get(src,seed,trail+(n,))+w
for c in range(4):print('TAP',c,[get(f'tap_{c}_{r}',seed) for r in range(4)],'BCO',get(f'bco{c}',seed))
# Every tile's local t_out valid timing measured51. Native node pin timing is inputcapture1 + node9 + outputcapture1=11.
seed.update({f't_out_{c}_{r}':get(f'tap_{c}_{r}',seed)+51 for c in range(4) for r in range(4)})
node=[];pending={(c,r) for c in range(4) for r in range(4)}
while pending:
 progress=False
 for c,r in list(pending):
  try:a=get(f'n_a_{c}_{r}',seed);b=get(f'n_b_{c}_{r}',seed)
  except KeyError as ex:
   missing=str(ex);continue
  node.append({'tile':[c,r],'a':a,'b':b,'aligned':a==b,'n_y':max(a,b)+11});seed[f'n_y_{c}_{r}']=max(a,b)+11;pending.remove((c,r));progress=True
 if not progress:
  print('MISSING',[(c,r,n) for c,r in pending for n in [f'n_a_{c}_{r}',f'n_b_{c}_{r}'] if n not in edges]);
  for c,r in pending:
   for n in [f'n_a_{c}_{r}',f'n_b_{c}_{r}']:
    try:get(n,seed)
    except KeyError as ex:print(n,'unknown',ex)
  break
print('NODES',node,'PENDING',sorted(pending))
print('ROOT',get('rs',seed),'FT',get('rs_o',{'rs_i':0}))
(S/'source_graph_diagnostic.json').write_text(json.dumps({'nodes':node,'root':get('rs',seed),'rs_feedthrough':get('rs_o',{'rs_i':0}),'edges':edges,'bco':[get(f'bco{c}',{f'bc{i}':0 for i in range(4)}) for c in range(4)],'source_sha256':{f:__import__('hashlib').sha256((S/f).read_bytes()).hexdigest() for f in ['qfd_c_b16_dv_fabric.sv','qfd_c_stn.sv','qfd_c_land.sv']}},indent=2)+'\n')
