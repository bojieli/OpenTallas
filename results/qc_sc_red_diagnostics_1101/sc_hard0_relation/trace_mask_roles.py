from pathlib import Path
from collections import defaultdict,deque,Counter
import re,json,subprocess
b=Path('.')
s=(b/'new_qfd_dv_s5_sc2_k79.sv').read_text()
gen=re.compile(r'generate if \(HARD_PINREG\) begin : \w+\n(.*?)\nend else begin : \w+\n.*?\nend endgenerate',re.S)
s,n=gen.subn(lambda m:m[1],s)
s=re.sub(r"HARD_PINREG\s*\?\s*1'b1\s*:\s*\w+","1'b1",s)
s=re.sub(r'HARD_PINREG\s*\?\s*\(([^()]*)\)\s*:\s*\w+',r'(\1)',s)
inst=re.compile(r'\b(qfd_s2_bmath_\w+)\s*#\(\.ID\((\d+)\)\)\s+(\w+)\((.*?)\);');port=re.compile(r'\.(\w+)\(([^()]*)\)')
adj=defaultdict(list);term=defaultdict(list);kind=Counter()
for m in inst.finditer(s):
 ps=dict(port.findall(m[4]));kind[m[1]]+=1
 if '_dff_' in m[1]:
  for p in ['D','R','C']:
   if p in ps:term[ps[p]].append({'instance':m[3],'primitive':m[1],'port':p})
 else:
  assert 'Y'in ps,m[1]
  for k,v in ps.items():
   if k!='Y':adj[v].append((ps['Y'],m[3]+':'+m[1]+'/'+k+'->Y'))
for lhs,rhs in re.findall(r'\bassign\s+([^=;]+)=([^;]+);',s):
 lhs=lhs.strip()
 if not re.fullmatch(r'(n_\d+|sc_pin_\w+)',lhs):continue
 for v in set(re.findall(r'\b(?:n_\d+|sc_pin_\w+)\b',rhs)):
  adj[v].append((lhs,'assign '+lhs+'='+rhs.strip()))
mp=json.loads(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','41612e22eac:results/qc_suc_restore_1101/sc_pin_candidate/source_map.json']))
reports=[]
for g in mp['reset_groups']:
 for c in g['captures']:
  start=c['ports']['Q'];q=deque([start]);prev={start:None};ends=[]
  while q:
   w=q.popleft()
   for t in term[w]:
    e=dict(t);e['net']=w
    if t['port'] in ['R','C']:
     path=[];v=w
     while prev[v] is not None:
      u,why=prev[v];path.append({'from':u,'to':v,'via':why});v=u
     e['path']=list(reversed(path))
    ends.append(e)
   for z,why in adj[w]:
    if z not in prev:prev[z]=(w,why);q.append(z)
  reports.append({'input_bit':g['bit'],'original_capture_instance':c['instance'],'masked_output':start,'visited_combinational_nets':len(prev),'terminal_counts':dict(Counter(t['port']for t in ends)),'asynchronous_R_or_clock_C_terminals':[t for t in ends if t['port'] in ['R','C']]})
out={'scope':'EXACT_HARD1_SOURCE_COMBINATIONAL_FANOUT_OF_15_RESETTABLE_DATA_CAPTURE_OUTPUTS','source':'98bbbbd8184','generate_branches_HARD1':n,'reports':reports,'total_async_R_or_clock_C_reach':sum(len(r['asynchronous_R_or_clock_C_terminals'])for r in reports),'limit':'Cuts at every register, excludes parent/top external reconnection, no glitch/analog/reset qualification or adoption inferred. Names do not classify signal function.'}
(b/'masked_capture_role_trace.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'total':out['total_async_R_or_clock_C_reach'],'rows':[{k:v for k,v in r.items()if k!='asynchronous_R_or_clock_C_terminals'}for r in reports]},indent=2))
