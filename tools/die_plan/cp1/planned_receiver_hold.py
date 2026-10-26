"""OpenROAD Python: plan explicit BUF-identity receiver delay rows on a CP1 proof vehicle.
No ODB mutation in default mode. --apply consumes that reviewed plan and writes a NEW ODB.
"""
import argparse,bisect,json,re
from pathlib import Path
import odb

p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);p.add_argument('--manifest',required=True);p.add_argument('--count',type=int,default=8);p.add_argument('--apply',action='store_true');a=p.parse_args()
db=odb.dbDatabase.create();odb.read_db(db,a.odb);blk=db.getChip().getBlock();u=blk.getDbUnitsPerMicron();m=db.findMaster('BUFx2_ASAP7_75t_R');assert m
if a.apply:
 j=json.load(open(a.manifest));assert j['count']==a.count
 import gzip
 truth={}
 for corner in ('TT','FF'):
  lib=next(Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*INVBUF_RVT_'+corner+'_*'))
  text=gzip.open(lib,'rt').read() if str(lib).endswith('.gz') else lib.read_text()
  match=re.search(r'cell\s*\(\s*\"?BUFx2_ASAP7_75t_R\"?\s*\)\s*\{',text);assert match,lib
  end=re.search(r'\n\s*cell\s*\(',text[match.end():]);body=text[match.end():match.end()+end.start()] if end else text[match.end():]
  assert re.search(r'function\s*:\s*\"?A\"?\s*;',body),(lib,'BUF identity missing')
  truth[corner]='Y=A'

 n=0
 for r in j['chains']:
  sink=blk.findITerm(r['sink']);assert sink and sink.getNet().getName()==r['old_net'],r
  prev=sink.getNet();sink.disconnect()
  for k,(x,y,orient) in enumerate(r['sites']):
   name=f'cp1_rxpad_{n}_{k}';assert not blk.findInst(name)
   inst=odb.dbInst.create(blk,m,name);nxt=odb.dbNet.create(blk,name+'_n');assert inst and nxt
   inst.findITerm('A').connect(prev);inst.findITerm('Y').connect(nxt)
   for it in inst.getITerms():
    st=it.getSigType()
    if st in ('POWER','GROUND'):
     pn=blk.findNet('VDD' if st=='POWER' else 'VSS');assert pn;it.connect(pn)
   inst.setOrient(orient);inst.setLocation(x,y);inst.setPlacementStatus('FIRM');prev=nxt
  sink.connect(prev);n+=1
 # Audit every actual connection and the chosen cell's true TT/FF Boolean function.
 def audit():
  for n,r in enumerate(j['chains']):
   net=blk.findITerm(r['sink']).getNet()
   for k in reversed(range(a.count)):
    inst=blk.findInst(f'cp1_rxpad_{n}_{k}');assert inst.getMaster().getName()==m.getName()
    assert inst.findITerm('Y').getNet().getName()==net.getName();net=inst.findITerm('A').getNet()
   assert net.getName()==r['old_net']
 audit()
 first=blk.findInst('cp1_rxpad_0_0').findITerm('A');saved=first.getNet()
 wrong=next(blk.findNet(r['old_net']) for r in j['chains'] if r['old_net']!=saved.getName())
 caught=False
 try:
  first.disconnect();first.connect(wrong)
  audit()
 except AssertionError:caught=True
 finally:first.disconnect();first.connect(saved)
 assert caught,'cross-input identity mutant was not detected'
 audit()
 Path(a.out+'.identity.json').write_text(json.dumps(dict(verdict='PASS',chains=len(j['chains']),buffers_per_chain=a.count,truth=truth,cross_input_mutant_caught=caught,registers_added=0),indent=2)+'\n')
 odb.write_db(db,a.out);print('CP1_RXPAD_IDENTITY PASS',len(j['chains']),'chains',a.count,'buffers/chain',a.out);raise SystemExit

report=json.load(open(a.manifest));external=set(report['external_ports']);expected=sum(report['selected'].values());rows=sorted(blk.getRows(),key=lambda r:r.getOrigin()[1]);ys=[];grid=[]
for row in rows:
 b=row.getBBox();site=row.getSite();sw=site.getWidth();rh=site.getHeight();ys.append(b.yMin());grid.append([b.xMin(),b.xMax(),b.yMin(),rh,sw,row.getOrient(),bytearray((b.xMax()-b.xMin())//sw+1)])
# Existing placements, including tap/decap/filler cells, are obstacles, never moved by this planner.
for inst in blk.getInsts():
 b=inst.getBBox();lo=max(0,bisect.bisect_right(ys,b.yMin())-1)
 for ri in range(lo,min(len(grid),bisect.bisect_left(ys,b.yMax())+1)):
  x0,x1,y,rh,sw,ori,occ=grid[ri]
  if y>=b.yMax() or y+rh<=b.yMin():continue
  s=max(0,(b.xMin()-x0)//sw);e=min(len(occ),(b.xMax()-x0+sw-1)//sw)
  if e>s:occ[s:e]=b'\1'*(e-s)
# Reserve space at every clock tap for the forthcoming local tree input buffers.
for bt in blk.getBTerms():
 if not re.fullmatch(r'clk(?:_t\d+)?',bt.getName()):continue
 b=bt.getBBox();cx=(b.xMin()+b.xMax())//2;cy=(b.yMin()+b.yMax())//2;clear=int(4.32*u)
 for ri in range(max(0,bisect.bisect_left(ys,cy-clear)-1),min(len(grid),bisect.bisect_right(ys,cy+clear))):
  x0,x1,y,rh,sw,ori,occ=grid[ri];s=max(0,(cx-clear-x0)//sw);e=min(len(occ),(cx+clear-x0+sw-1)//sw)
  if e>s:occ[s:e]=b'\1'*(e-s)

def first_dffs(net):
 todo=[net];seen=set();found={}
 while todo:
  net=todo.pop()
  if net.getId() in seen:continue
  seen.add(net.getId())
  for it in net.getITerms():
   if it.getIoType()!='INPUT':continue
   inst=it.getInst();master=inst.getMaster().getName()
   if 'DFF' in master and it.getMTerm().getName()=='D':found[inst.getName()+'/D']=it
   elif re.match(r'^(BUF|INV|HB)',master):
    for ot in inst.getITerms():
     if ot.getIoType()=='OUTPUT' and ot.getNet():todo.append(ot.getNet())
 return found
chains=[];used=set();w=m.getWidth();h=m.getHeight();reach=int(40*u)
for bt in blk.getBTerms():
 base=re.sub(r'\[\d+\]$','',bt.getName())
 if base not in external:continue
 found=first_dffs(bt.getNet());assert len(found)==1,(bt.getName(),list(found))
 sinkname,sink=next(iter(found.items()));assert sinkname not in used;used.add(sinkname)
 ib=sink.getInst().getBBox();sx=(ib.xMin()+ib.xMax())//2;sy=ib.yMin();best=None
 lo=max(0,bisect.bisect_left(ys,sy-reach));hi=min(len(grid),bisect.bisect_right(ys,sy+reach))
 for ri in sorted(range(lo,hi),key=lambda i:abs(ys[i]-sy)):
  x0,x1,y,rh,sw,ori,occ=grid[ri]
  if h!=rh:continue
  dy=abs(y-sy)
  if best and dy>best[0]:break
  ns=(a.count*w+sw-1)//sw;pattern=b'\0'*ns;left=max(0,(sx-reach-x0)//sw);right=min(len(occ),(sx+reach-x0)//sw);mid=max(left,min(right,(sx-x0)//sw))
  candidates=[occ.find(pattern,mid,right),occ.rfind(pattern,left,min(len(occ),mid+ns))]
  for c in candidates:
   if c<0:continue
   score=abs(x0+c*sw+a.count*w//2-sx)+dy
   if score<=reach and (best is None or score<best[0]):best=(score,ri,c,ns)
 assert best,('no reviewed receiver-pad row within40um',bt.getName(),sinkname)
 score,ri,c,ns=best;x0,x1,y,rh,sw,ori,occ=grid[ri];occ[c:c+ns]=b'\1'*ns
 sites=[[x0+c*sw+k*w,y,ori] for k in range(a.count)]
 chains.append(dict(port=bt.getName(),sink=sinkname,old_net=sink.getNet().getName(),sink_xy=[sx,sy],sites=sites,max_distance_um=score/u))
assert len(chains)==expected,(len(chains),expected)
j=dict(schema='opentallas.cp1.planned_receiver_hold.v1',source_odb=a.odb,master=m.getName(),count=a.count,dbu=u,master_wh_dbu=[w,h],chains=chains,added_cells=len(chains)*a.count,added_area_um2=len(chains)*a.count*w*h/u**2,identity='Every chain is non-inverting BUF A->Y and terminates at the original D pin; apply audits original net identity',clock_target_tt_ff_ps=[250,202.5],original_external_in_min_ps=-40,cycles='No added registers; zero cycle cost conditional on measured833ps TT setup')
Path(a.out).write_text(json.dumps(j,indent=1)+'\n');print('CP1_RXPAD_PLAN PASS',len(chains),'chains',j['added_cells'],'cells',j['added_area_um2'],'um2',max(r['max_distance_um'] for r in chains),'um')
