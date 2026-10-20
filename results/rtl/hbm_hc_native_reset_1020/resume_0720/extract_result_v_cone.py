import gzip,re,json,hashlib
from pathlib import Path
raw=Path('native.v').read_bytes();text=raw.decode();models=gzip.decompress(Path('cells.v.gz').read_bytes()).decode()
dirs={}
for m in re.finditer(r'module (\w+)\([^;]*;(.+?)endmodule',models,re.S):
 body=m.group(2);dirs[m.group(1)]={d:re.findall(r'(?m)^  '+d+r' (\w+);',body)for d in ['input','output']}
instances={};drivers={};aliases={}
for line in text.splitlines():
 a=re.match(r'\s*assign (\w+) = (.+);',line)
 if a:aliases[a[1]]=(a[2],line);continue
 m=re.match(r'\s*(\w+) (\w+) \((.+)\);',line)
 if not m or m[1] not in dirs:continue
 pins=dict(re.findall(r'\.(\w+)\(([^)]+)\)',m[3]));instances[m[2]]=(m[1],pins,line)
 for p in dirs[m[1]]['output']:
  if p in pins:drivers[pins[p]]=m[2]
queue=['result_v'];seen=set();picked=set();used_alias={};roots=set()
ports={'clk','rst_n','launch','mixes','bases','scales'}
while queue:
 n=queue.pop()
 if n in seen:continue
 seen.add(n)
 if n in aliases:
  rhs,line=aliases[n];used_alias[n]=line
  queue.extend(x for x in re.findall(r'\b[A-Za-z_]\w*\b',rhs)if x not in ['h','b','d'])
 elif n in drivers:
  inst=drivers[n]
  if inst not in picked:
   picked.add(inst);typ,pins,line=instances[inst]
   for p in dirs[typ]['input']:
    sig=pins[p]
    if "'" not in sig:queue.append(sig)
 elif n in ports:roots.add(n)
 else:raise RuntimeError('unresolved exact cone root '+n)
lines=['module native_result_v_cone(input wire clk,rst_n,launch,input wire [767:0]mixes,bases,input wire [95:0]scales,output wire result_v);']
nets=sorted(seen-ports-{'result_v'});lines+=['wire '+','.join(nets)+';']
lines += [instances[n][2]for n in sorted(picked)] + [used_alias[n]for n in sorted(used_alias)]+['endmodule']
out='\n'.join(lines)+'\n';Path('native_result_v_cone.v').write_text(out)
rep=dict(full_graph_sha256=hashlib.sha256(raw).hexdigest(),cone_sha256=hashlib.sha256(out.encode()).hexdigest(),all_cell_input_roles_followed=True,sequential_data_clock_and_async_inputs_included=True,selected_instances=len(picked),selected_instance_names=sorted(picked),roots=sorted(roots),cells={t:sum(instances[n][0]==t for n in picked)for t in sorted({instances[n][0]for n in picked})})
Path('cone_receipt.json').write_text(json.dumps(rep,indent=2)+'\n');print('RV_CONE',len(picked),sorted(roots))
