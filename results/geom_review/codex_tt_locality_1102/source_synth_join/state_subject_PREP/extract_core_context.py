import re,json,hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();lines=s.splitlines();call=[l for l in lines if l.startswith('qfd_tt_ctlm_dv_wtn ') and '.u_wtn ' in l];assert len(call)==1
producers={}
for line in lines:
 m=re.fullmatch(r'assign\s+(n_\d+)\s*=\s*([^;]+);',line.strip())
 if m:producers[m[1]]=dict(kind='assign',rhs=m[2],text=line)
 m=re.search(r'\b(qfd_bmath_dff_\w+)\s*#\((.*?)\)\s*(\w+)\((.*)\);',line)
 if m:
  ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[4]));q=ports.get('Q')
  if q:producers[q]=dict(kind=m[1],params=m[2],instance=m[3],ports=ports,text=line)
path=[];n='n_96145';seen=set()
while n in producers:
 assert n not in seen;seen.add(n);v=producers[n];path.append(dict(net=n,**v));n=v['rhs'] if v['kind']=='assign' else v['ports']['D']
x=dict(core_source_sha256=hashlib.sha256(s.encode()).hexdigest(),core_module_header=next(l for l in lines if l.startswith('module ')),actual_wtn_callsite=call[0],clock_alias=producers['n_3159'],control_reset_source='n_96145',reset_trace=path,reset_trace_terminal=n,reset_registered_edges=sum(v['kind']!='assign' for v in path));print(json.dumps(x,indent=1))
