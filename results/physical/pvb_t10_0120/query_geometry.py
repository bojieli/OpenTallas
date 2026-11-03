from pathlib import Path
import re,json
root=Path('/srv/opentallas-scratch2/claude/codex-pvb-tt-0108/t10');rows=[json.loads(v) for v in Path('/srv/opentallas-scratch2/claude/codex-pvb-tt-0108/remaining_drivers.jsonl').read_text().splitlines()]
names={n.lstrip('\\').replace('\\','') for r in rows for n,_,_ in r['links']};nets={r['net'] for r in rows};pos={};routes={};active=None;parts=[]
for line in next(root.glob('run/results/asap7/*/base/6_final.def')).open():
 m=re.match(r'\s*-\s+(\S+)\s+(\S+)\s+.*?\+ (?:PLACED|FIXED) \( (\d+) (\d+) \)',line)
 if m and m[1].replace('\\','') in names:pos[m[1].replace('\\','')]=dict(master=m[2],xy=[int(m[3])/1000,int(m[4])/1000])
 m=re.match(r'\s*-\s+(\S+)\s+',line)
 if m and m[1] in nets:active=m[1];parts=[line]
 elif active:
  parts.append(line)
  if ';' in line:routes[active]=''.join(parts);active=None
for r in rows:
 r['placements']={n:pos[n.lstrip('\\').replace('\\','')] for n,_,_ in r['links']};paths=[]
 for seg in re.split(r'\b(?:ROUTED|NEW)\s+(M\d+)\s+',routes.get(r['net'],''))[1:][1::2]:
  xy=[]
  for x,y in re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',seg):
   if (x=='*' or y=='*') and not xy:continue
   xy.append([xy[-1][0] if x=='*' else int(x)/1000,xy[-1][1] if y=='*' else int(y)/1000])
  if xy:paths.append(xy)
 r['routed_paths']=paths;r['routed_length_um']=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for xy in paths for a,b in zip(xy,xy[1:]))
print(json.dumps(rows,indent=2))
