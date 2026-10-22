# Archived actual-case reservation vehicle; argument is the preserved input directory.
import sys,re,json,collections
from pathlib import Path
sys.path.insert(0,'tools/qwen_kv_die');import kv_lane_orientation as L;from kv_fwd_lanes import expr_bits,INST,CONN
p=Path(sys.argv[1]); report=json.loads((p/'orientation.json').read_text());changed={x['instance'] for x in report['changes']}; txt=(p/'elements.lef').read_text();macros={m['name']:m for m in L.C.parse_lef(txt)}
# Attach direction (shared LEF reader intentionally omits direction).
cur=pin=None;directions={}
for line in txt.splitlines():
 s=line.strip().split()
 if not s:continue
 if s[0]=='MACRO':cur=s[1]
 elif s[0]=='PIN':pin=s[1]
 elif s[0]=='DIRECTION' and cur and pin:directions[cur,pin]=s[1]
for m in macros.values():m['pd']={x['name']:x for x in m['pins']}
text=(p/'die.v').read_text();wires={m[1]:int(m[0])+1 for m in re.findall(r'wire\s+\[(\d+):0\]\s+(\S+);',text)};insts={}
for line in text.splitlines():
 m=INST.match(line)
 if m:insts[m[3]]=(m[2],dict(CONN.findall(m[4])))
placements=[]
for f in ('place.tcl','place.adapted.tcl'):
 placements.append({n:(float(x)*1000,float(y)*1000,o) for n,x,y,o in re.findall(r'ot_mts::place \[\$_blk findInst (\S+)\] (\S+) (\S+) (\S+)',(p/f).read_text())})
incident={}
for n in changed:
 for port,expr in insts[n][1].items():
  for bit,b in enumerate(expr_bits(expr,wires)):
   if b not in ('0','1'):incident.setdefault(b,[]).append((n,port,bit))
ends=collections.defaultdict(list)
for n,(master,cs) in insts.items():
 for port,expr in cs.items():
  for bit,b in enumerate(expr_bits(expr,wires)):
   if b in incident:ends[b].append((n,port,bit))
def points(ep,index):
 n,port,bit=ep;master=insts[n][0];m=macros.get(master);pl=placements[index].get(n)
 if m is None or pl is None:return []
 pin=m['pd'].get(port+f'[{bit}]') or (m['pd'].get(port) if bit==0 else None)
 if pin is None:return []
 x,y,o=pl;return [(x+(q[0]+q[2])/2,y+(q[1]+q[3])/2) for lay,r in pin['rects'] for q in [L.C.transform_rect(r,o,m['W'],m['H'])]]
def direction(ep):
 n,port,bit=ep;mst=insts[n][0];return directions.get((mst,port+f'[{bit}]'),directions.get((mst,port)))
rows=[];unmeasured=[]
for b,touched in incident.items():
 es=ends[b];drivers=[e for e in es if direction(e) in ('OUTPUT','INOUT')];loads=[e for e in es if direction(e) in ('INPUT','INOUT')]
 for s in drivers:
  for d in loads:
   if s==d or not(s[0] in changed or d[0] in changed):continue
   # root clock/reset fanout is CTS/release-window qualified; lane transport is a fixed hop.
   tp=any(e[0] in changed and e[1] in ('a','b','ck_o','ckf','ea','eb') for e in (s,d))
   widths=[int(insts[e[0]][0].rsplit('_',1)[1]) for e in (s,d) if insts[e[0]][0].startswith(('qkd_rlysh','qkd_landsh'))]
   width=max(widths,default=1);reach=400 if width<=36 else 370 if width<=296 else 340
   spans=[]
   for i in (0,1):
    a,c=points(s,i),points(d,i)
    spans.append(min((abs(x-u)+abs(y-v))/1000 for x,y in a for u,v in c) if a and c else None)
   row=dict(net=b,src=s,dst=d,before=spans[0],after=spans[1],reach=reach,transport=tp)
   if None in spans:unmeasured.append(row)
   else:rows.append(row)
