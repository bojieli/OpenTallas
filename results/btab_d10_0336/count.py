from pathlib import Path
from collections import defaultdict,Counter
import json
p=Path('/srv/opentallas-scratch2/claude/codex-btab-0336/grt_segments/segments.txt')
cut=252500
windows={'hotspot1um':(89000,90000),'central_street':(58344,90720),'macro_body_top':(90720,131784),'north_margin':(131784,151200)}
cross={k:defaultdict(set) for k in windows};bins=defaultdict(lambda:defaultdict(set));m5h=set();net='';m5all=Counter()
for line in p.open():
 a=line.split()
 if len(a)==1 and a[0] not in ('(',')'):net=a[0]
 if len(a)!=6:continue
 try:x0,y0,x1,y1=map(int,(a[0],a[1],a[3],a[4]))
 except ValueError:continue
 if a[2]!=a[5]:continue
 layer=a[2]
 if layer=='M5':
  m5all['segments']+=1
  if y0==y1 and x0!=x1:m5all['horizontal_segments']+=1;m5h.add(net)
 if y0!=y1 or not min(x0,x1)<cut<max(x0,x1):continue
 bins[(y0//10000)*10][layer].add(net)
 for w,(lo,hi) in windows.items():
  if lo<=y0<hi:cross[w][layer].add(net)
res={'cut_x_um':252.5,'windows':{w:{l:len(n) for l,n in layers.items()} for w,layers in cross.items()},'crossings_by_y10um':{str(y):{l:len(n) for l,n in ls.items()} for y,ls in sorted(bins.items())},'all_M5':dict(m5all),'M5_nonpreferred_horizontal_nets':len(m5h),'guide_only':'Global-route segment centre lines, not detailed-route track assignment. Each crossing counted per unique net/layer/window.'}
(p.parent/'crossings.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
