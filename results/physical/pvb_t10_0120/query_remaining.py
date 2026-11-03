from pathlib import Path
import re,json,collections
p=next(Path('/srv/opentallas-scratch2/claude/codex-pvb-tt-0108/t10/run/results/asap7').glob('*/base/6_final.v'));insts={};links=collections.defaultdict(list)
for b in p.read_text().split(';'):
 m=re.match(r'\s*([A-Za-z_]\w+)\s+(\S+)\s+\(',b)
 if not m or m[1]=='module':continue
 c,n=m.groups();pairs=dict(re.findall(r'\.(\w+)\(\s*([^)]*?)\s*\)',b));insts[n]=(c,pairs)
 for pin,net in pairs.items():links[net].append((n,c,pin))
for name,pin in [('_051067_','A1'),('_053968_','A'),('_055851_','A1'),('_050897_','A1'),('_051160_','A1'),('_049808_','C2')]:
 c,ps=insts[name];net=ps[pin];print(json.dumps(dict(pin=name+'/'+pin,master=c,net=net,links=links[net])))
