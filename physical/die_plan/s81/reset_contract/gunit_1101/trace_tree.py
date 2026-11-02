from pathlib import Path
import json,re,hashlib,collections
B=Path('/srv/opentallas-scratch2/claude/die-s81-47/ck/T48/run/kit/clock');P=B/'ctree.v';txt=P.read_text();drivers={}; cells={}
for ln,line in enumerate(txt.splitlines(),1):
 a=re.fullmatch(r'\s*assign\s+(\S+)\s*=\s*(\S+)\s*;',line)
 if a:drivers[a[1]]=dict(kind='assign',input=a[2],line=ln,text=line.strip());continue
 c=re.fullmatch(r'\s*(\w+)\s+(\w+)\s*\((.*)\);',line)
 if c and c[1] != "module":
  ports=dict(re.findall(r'\.(\w+)\(([^)]+)\)',c[3]));cells[c[2]]=c[1]
  if set(ports)=={'A','Y'}:drivers[ports['Y']]=dict(kind='cell',cell=c[1],inst=c[2],input=ports['A'],line=ln,text=line.strip())
rows=[]
for part,tap,bg in [('gunit','clk','clk_region_std_bg_61_0'),('bk_sel','clk','clk_region_std_bg_70_0'),('s_2N_x06','clk_t14','clk_region_std_bg_51_0')]:
 out='t_'+part+'__'+tap;net=out;seen=set();trace=[]
 while net in drivers and net not in seen:
  seen.add(net);r=drivers[net];trace.append(dict(output=net,**r));net=r['input']
 rows.append(dict(bound_region_port=bg,physical_part=part,physical_tap=tap,ctree_port=out,terminal=net,closed_to_root=net=='root',cell_counts=dict(collections.Counter(r['cell'] for r in trace if r['kind']=='cell')),trace=trace))
d=dict(source=str(P),source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),all_cell_types=dict(collections.Counter(cells.values())),paths=rows)
print(json.dumps(d,indent=2))
