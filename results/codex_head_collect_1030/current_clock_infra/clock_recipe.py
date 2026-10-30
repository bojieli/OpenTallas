"""OpenROAD Python: export/import/verify one rooted CTS infrastructure recipe.
Environment ACTION=export|import|verify INPUT_ODB RECIPE OUTPUT_ODB REPORT ROOT_CLOCK(default clk).
Import checks exact connectivity/masters/coordinates first, then fixes the real connected buffer tree in the physical ODB.
It never adds a verdict-only island or changes a flop, macro, clock pin, clock net, RTL or cycle.
"""
import os,json,hashlib,re
from pathlib import Path
import odb

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def point(inst,dbu):
 b=inst.getBBox();return [(b.xMin()+b.xMax())/(2*dbu),(b.yMin()+b.yMax())/(2*dbu)]
def extract(db,root):
 b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();p=b.findBTerm(root)
 if p is None or p.getNet() is None:raise ValueError('missing actual clock root '+root)
 bb=p.getBBox();rootxy=[(bb.xMin()+bb.xMax())/(2*u),(bb.yMin()+bb.yMax())/(2*u)]
 queue=[p.getNet()];seen=set();cells={};nets={};reached=set();edges=[];unexpected=[]
 while queue:
  n=queue.pop(0)
  if n.getName() in seen:continue
  seen.add(n.getName());end=[];drivers=[];loads=[]
  for q in n.getBTerms():
   z='PORT:'+q.getName();end.append(z)
   if q.getIoType()=='INPUT':drivers.append((z,rootxy))
  for it in n.getITerms():
   i=it.getInst();m=i.getMaster();pin=it.getMTerm();nm=i.getName();z=nm+'/'+pin.getName();end.append(z)
   if pin.getIoType()=='OUTPUT':drivers.append((z,point(i,u)))
   elif pin.getIoType()=='INPUT':
    reached.add(z);loads.append((z,point(i,u)))
    if re.match(r'^(BUF|INV|HB|CKINV|CKBUF|CLKBUF)',m.getName()):
     x,y=i.getLocation();cells[nm]=dict(name=nm,master=m.getName(),xy_dbu=[x,y],orient=i.getOrient(),center_um=point(i,u))
     for ot in i.getITerms():
      if ot.getMTerm().getIoType()=='OUTPUT' and ot.getNet() is not None:queue.append(ot.getNet())
    elif not(m.isBlock() or 'DFF' in m.getName()):unexpected.append(z+' master '+m.getName())
  if len(drivers)!=1:raise ValueError('clock net requires exactly one actual driver: '+n.getName())
  for z,xy in loads:
   src,sp=drivers[0];edges.append(dict(net=n.getName(),driver=src,sink=z,driver_um=sp,sink_um=xy,l1_um=round(abs(xy[0]-sp[0])+abs(xy[1]-sp[1]),4)))
  nets[n.getName()]=dict(name=n.getName(),sig_type=n.getSigType(),endpoints=sorted(end))
 if unexpected:raise ValueError('unexpected clock tree capture '+str(unexpected[:8]))
 unrooted=[]
 for i in b.getInsts():
  if not(i.getMaster().isBlock() or 'DFF' in i.getMaster().getName()):continue
  for it in i.getITerms():
   mt=it.getMTerm()
   if mt.getIoType()=='INPUT' and (mt.getSigType()=='CLOCK' or mt.getName() in ('CLK','CK','clk')) and it.getNet() is not None:
    z=i.getName()+'/'+mt.getName()
    if z not in reached:unrooted.append(z)
 if unrooted:raise ValueError('unrooted actual clock pins '+str(unrooted[:8]))
 # Placement of the real clock infrastructure may not overlap hard macros.
 macros=[i for i in b.getInsts() if i.getMaster().isBlock()];over=[]
 for n in cells:
  cb=b.findInst(n).getBBox()
  for m in macros:
   mb=m.getBBox()
   if cb.xMin()<mb.xMax() and mb.xMin()<cb.xMax() and cb.yMin()<mb.yMax() and mb.yMin()<cb.yMax():over.append(n+'@'+m.getName())
 if over:raise ValueError('clock cell overlaps macro '+str(over[:8]))
 die=b.getDieArea();core=b.getCoreArea()
 pins=sorted([dict(name=q.getName(),io=q.getIoType(),sig=q.getSigType(),boxes=sorted([[g.getTechLayer().getName(),g.xMin(),g.yMin(),g.xMax(),g.yMax()] for bp in q.getBPins() for g in bp.getBoxes()])) for q in b.getBTerms()],key=lambda x:x['name'])
 macro_contract=sorted([dict(name=i.getName(),master=i.getMaster().getName(),xy_dbu=list(i.getLocation()),orient=i.getOrient()) for i in macros],key=lambda x:x['name'])
 contract=dict(die_dbu=[die.xMin(),die.yMin(),die.xMax(),die.yMax()],core_dbu=[core.xMin(),core.yMin(),core.xMax(),core.yMax()],pins=pins,macros=macro_contract,config_sha256=sha(Path(os.environ.get('CONFIG_MK','/work/config.mk'))),sdc_sha256=sha(Path(os.environ.get('CONSTRAINT_SDC','/work/constraint.sdc'))))
 return dict(physical_contract=contract,schema='opentallas.rooted_cts_recipe.v1',root_port=root,root_net=p.getNet().getName(),root_um=rootxy,dbu_per_um=u,cells=sorted(cells.values(),key=lambda x:x['name']),nets=sorted(nets.values(),key=lambda x:x['name']),edges=edges,edge_count=len(edges),max_center_leg_um=max([e['l1_um'] for e in edges],default=0),unrooted_clock_pins=unrooted,clock_cells_on_macros=over)
def compare(want,got):
 for k in ('physical_contract','root_port','root_net','root_um','dbu_per_um','cells','nets'):
  if want[k]!=got[k]:raise ValueError('actual rooted clock recipe mismatch: '+k)
# Sink flop legalization may move sink pins; the clock cells and graph must stay exact.
# Fresh actual legs are remeasured by extract(), never copied from the receipt.
act=os.environ.get('ACTION','export');inp=Path(os.environ['INPUT_ODB']);recipe=Path(os.environ['RECIPE']);report=Path(os.environ.get('REPORT',str(recipe)+'.report.json'));root=os.environ.get('ROOT_CLOCK','clk');db=odb.dbDatabase.create();db=odb.read_db(db,str(inp));b=db.getChip().getBlock()
if report.exists():raise FileExistsError('immutable report already exists; select a new REPORT path: '+str(report))
try:
 got=extract(db,root)
 if got['max_center_leg_um']>220:raise ValueError('actual clock leg exceeds220um: '+str(got['max_center_leg_um']))
 if act=='export':
  got.update(input_odb_sha256=sha(inp),baseline_stage='actual 4_cts before signal GRT',frozen_clock_status='not imported yet')
  recipe.write_text(json.dumps(got,indent=1)+'\n')
 elif act in ('import','verify'):
  want=json.loads(recipe.read_text());compare(want,got)
  if act=='import':
   for c in want['cells']:
    i=b.findInst(c['name']);i.setPlacementStatus('FIRM');i.setDoNotTouch(True)
   for n in want['nets']:b.findNet(n['name']).setDoNotTouch(True)
   compare(want,extract(db,root));odb.write_db(db,os.environ['OUTPUT_ODB'])
  else:
   bad=[c['name'] for c in want['cells'] if b.findInst(c['name']).getPlacementStatus() not in ('FIRM','LOCKED','COVER')]
   if bad:raise ValueError('clock recipe was not physically imported: '+str(bad[:8]))
   unprotected=[c['name'] for c in want['cells'] if not b.findInst(c['name']).isDoNotTouch()]+[n['name'] for n in want['nets'] if not b.findNet(n['name']).isDoNotTouch()]
   if unprotected:raise ValueError('clock infrastructure was not protected against timing edits: '+str(unprotected[:8]))
 else:raise ValueError('unknown ACTION '+act)
 result=dict(verdict='PASS',action=act,script_sha256=sha(Path(__file__)),actual_clock_cells=len(got['cells']),edge_count=got['edge_count'],max_center_leg_um=got['max_center_leg_um'],unrooted_clock_pins=0,clock_cells_on_macros=0,added_flops=0,added_cycles=0)
 report.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
except Exception as e:
 report.write_text(json.dumps(dict(verdict='FAIL',action=act,error=str(e)),indent=1)+'\n');raise
