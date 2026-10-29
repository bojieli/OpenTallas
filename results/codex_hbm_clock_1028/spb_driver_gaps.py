"""Reserve small native clock-driver bays inside existing SPB flop banks.
No new state/stage, changed pins, PHY PG envelope or source selection.
Usage: script ORIGINAL_PLACEMENT CLOCK_BUDGET PROBE_LEF OUTDIR
"""
from pathlib import Path
import json,sys,math,re,copy
P,B,L,O=map(Path,sys.argv[1:]);O.mkdir(exist_ok=True,parents=True)
p=json.load(open(P));old=copy.deepcopy(p);budget=json.load(open(B));boxes=list(p['physical_envelopes_um'].values())
def hit(a,b):return a[0]<b[2]-1e-7 and b[0]<a[2]-1e-7 and a[1]<b[3]-1e-7 and b[1]<a[3]-1e-7
def rect(pt,w=1.35,h=.27):return [pt[0],pt[1],pt[0]+w,pt[1]+h]
gaps=[];moves=[]
for tap in budget['tap_rows']:
 x,y=tap['xy'];g=[round(round((x-2.16)/.054)*.054,6),round(math.floor(y/.54)*.54,6)];g += [round(g[0]+4.32,6),round(g[1]+1.08,6)]
 if any(hit(g,b)for b in boxes):raise ValueError(('clock bay hits fixed PG/core envelope',tap,g))
 banks=[e for e in p['entries']if hit(g,e['bay_rect_um'])]
 if not banks:continue
 for e in banks:
  sites=e['sites_um'];bad=[i for i,q in enumerate(sites)if hit(g,rect(q))]
  if not bad:continue
  bx,by,bxx,byy=e['bay_rect_um'];candidates=[]
  for row in range(33):
   for col in range(16):
    q=[round(bx+col*2.268,6),round(by+row*.27,6)];r=rect(q)
    if hit(g,r)or any(hit(z,r)for z in boxes):continue
    if any(hit(rect(pt),r)for j,pt in enumerate(sites)if j not in bad):continue
    candidates.append(q)
  # A one-to-one minimum-Manhattan selection keeps every original bit index.
  for i in bad:
   q=sites[i];new=min(candidates,key=lambda z:abs(z[0]-q[0])+abs(z[1]-q[1]));candidates.remove(new);sites[i]=new
   moves.append(dict(instance=e['instance'],stage=e['stage'],bit=i,old=q,new=new))
 gaps.append(dict(port=tap['port'],rect_um=g,native_master='CKINVDCx16_ASAP7_75t_R',native_cell_um=[1.62,.27]))
# Exact endpoints from the existing signal-only probe LEF (same plan pin files).
text=L.read_text();pins={}
for name,block in re.findall(r'MACRO (\S+)(.*?)END \1',text,re.S):
 d={}
 for pn,body in re.findall(r' PIN (\S+)\s+(.*?)\n END \1',block,re.S):
  m=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',body)
  if m:
   a,b,c,dv=map(float,m.groups());d[pn]=[(a+c)/2,(b+dv)/2]
 pins[name]=d
def ports(macro,port,width,origin):return [[pins[macro][f'{port}[{i}]'][0]+origin[0],pins[macro][f'{port}[{i}]'][1]+origin[1]]for i in range(width)]
lk=[103.68,0];ep=[181.44,1088.64]
endpoints={'u_hbm_spb0_rx':(ports('PHY_SPB_PROBE','rx',512,lk)+ports('PHY_SPB_PROBE','st',2,lk),ports('EP_SPB_PROBE','sd_rx',512,ep)+ports('EP_SPB_PROBE','sd_st',2,ep)), 'u_hbm_spb0_tx':(ports('EP_SPB_PROBE','sd_tx',512,ep),ports('PHY_SPB_PROBE','tx',512,lk))}
summary=[]
for inst,(src,dst)in endpoints.items():
 es=sorted((e for e in p['entries']if e['instance']==inst),key=lambda e:e['stage']);seq=[src]+[[[x+.675,y+.135]for x,y in e['sites_um']]for e in es]+[dst]
 hops=[max(abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(aa,bb))for aa,bb in zip(seq,seq[1:])];assert max(hops)<=405,(inst,hops)
 summary.append(dict(instance=inst,max_per_bit_hops_um=hops,maximum_um=max(hops),width=len(src),stages=4))
rs=[]
for e in p['entries']:
 for x,y in e['sites_um']:
  assert abs(x/.054-round(x/.054))<1e-6 and abs(y/.27-round(y/.27))<1e-6
  r=rect([x,y]);assert not any(hit(r,b)for b in boxes);assert not any(hit(r,g['rect_um'])for g in gaps);rs.append(r)
for i,r in enumerate(rs):assert not any(hit(r,z)for z in rs[i+1:]),i
assert len(rs)==4104 and all(e['bay_fill']<=.6 for e in p['entries'])
p['summary']=summary;p['status']='PASS-COND source-identical driver-gap bank candidate; physical clock import and G2 pending';p['clock_driver_gaps']=gaps;p['previous_placement_sha256']=__import__('hashlib').sha256(P.read_bytes()).hexdigest();p['driver_gap_moves']=moves
(O/'placement.json').write_text(json.dumps(p,indent=1)+'\n');(O/'gap_summary.json').write_text(json.dumps(dict(flops=len(rs),moved_flops=len(moves),gaps=gaps,summary=summary,added_cycles=0,source_changed=False),indent=1)+'\n');print('SPB_GAPS_PASS',len(rs),'moves',len(moves),'gaps',len(gaps),summary)
