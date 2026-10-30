#!/usr/bin/env python3
import sys,re,json,collections
from pathlib import Path
K,O=map(Path,sys.argv[1:3]);names=json.load(open(O/'register_groups.json'))
s=next(K.glob('run/results/asap7/*/base/1_synth.v')).read_text()
ff=re.findall(r'^\s*(\S*DFF\S*)\s+\\(\S+)\s*\(',s,re.M)
counts=collections.Counter();unknown=[];aliases=[]
for master,nm in ff:
 n=nm.split('$')[0];g=names.get(n)
 if g:pass
 elif m:=re.match(r'u_fcore.core.gthreshold\[([0-3])\].local_copy.value\[',n):g='threshold'+m[1]
 elif m:=re.match(r'u_fcore.core.ties\[([0-3])\]',n):g='threshold'+m[1]
 elif m:=re.match(r'u_fcore.core.gq\[([0-3])\].',n):g='q'+m[1]
 elif m:=re.match(r'u_fcore.core.hist\[([0-9]+)\]',n):g='q'+str(int(m[1])//64)
 elif m:=re.match(r'u_fcore.core.selected_line\[([0-9]+)\]',n):g='q'+str(int(m[1])//592)
 elif m:=re.match(r'u_fcore.core.(selected|selected_v|qfault)\[([0-3])\]',n):g='q'+m[2]
 elif n.startswith('u_fcore.core.'):g='root'
 elif n.startswith('u_fcore.'):unknown.append(n);g='UNKNOWN'
 else:g='boundary_or_infra'
 counts[g]+=1
actual={n.split('$')[0] for _,n in ff}
missing=[n for n in names if n not in actual]
result=dict(total_ff=len(ff),group_counts=counts,unknown=unknown,missing_exact_names=missing)
(O/'mapped_ff_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
