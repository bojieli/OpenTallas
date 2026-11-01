from pathlib import Path
import json,copy,hashlib,math,re
R=Path('/srv/opentallas-scratch2/claude/codex-s81-cohort-1101/ves_w1728');W=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-cohort-1101');B=W/'results/geom_review/codex_ves_w1728_1101'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
D=json.load(open(R/'baseline_plan.json'));O=copy.deepcopy(D)
pd=json.load(open(B/'ot_s81sl_ve_s_tpl_w1728.json'));pd['lef']=str((B/'ot_s81sl_ve_s_tpl_w1728.lef').relative_to(W));(B/'ot_s81sl_ve_s_tpl_w1728.json').write_text(json.dumps(pd,indent=2)+'\n')
pinpath=str(B/'ot_s81sl_ve_s_tpl_w1728.json');lef=pd['lef'];rows=[];tapmoves=[];bad=[]
def box(c):
 x,y=c['origin_um'];tx,ty=c.get('track_offset_um',[0,0]);w,h=c['outline_um'];return[x+tx,y+ty,x+tx+w,y+ty+h]
def gap(a,b):return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))
for tn,t in D['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_s81sl_ve_s':continue
  assert c['outline_um']==[172.8,345.6],(tn,c['outline_um'])
  old=box(c);c.update(outline_um=[172.8,345.6],lef=lef,pins_file=pinpath);new=box(c)
  near=[(gap(new,box(q)),q['inst']) for q in t['hard_cores'] if q is not c and not q['inst'].startswith(c['inst']+'.')]
  mind,who=min(near,default=(float('inf'),None))
  overlap=[q['inst'] for q in t['hard_cores'] if q is not c and not q['inst'].startswith(c['inst']+'.') and min(new[2],box(q)[2])-max(new[0],box(q)[0])>1e-6 and min(new[3],box(q)[3])-max(new[1],box(q)[1])>1e-6]
  tw,th=t['outline_um'];inside=new[0]>=0 and new[1]>=0 and new[2]<=tw and new[3]<=th
  if overlap or not inside:bad.append(dict(type=tn,overlap=overlap,inside=inside))
  orient=c.get('orient','R0');delta=0 # canonical plan already applied W172.8 transform; never double-retap
  for tp in t.get('clock',{}).get('taps',[]):
   if tp.get('name','').startswith(c['inst']+'.') and delta:
    oldxy=list(tp['xy']);tp['xy'][0]=round(tp['xy'][0]+delta,6);tapmoves.append(dict(type=tn,name=tp['name'],old=oldxy,new=tp['xy'],reason='native localclk unchanged; mirrored widened outline changes type-coordinate transform'))
  rows.append(dict(type=tn,inst=c['inst'],orient=orient,old_box=old,new_box=new,nearest_gap_um=mind,nearest=who,overlap=overlap,inside=inside))
assert rows and not bad,bad
(R/'plan_W1728.json').write_text(json.dumps(D,indent=1)+'\n')
sl=json.load(open(R/'old_master_slice.json'));sl['outline_um']=[172.8,345.6];sl['master_plan_sha256']=sha(R/'plan_W1728.json');sl['frozen']=False
for rect in sl.get('pg_obstructions_um',{}).get('M4',[]):
 if abs(rect[2]-159.84)<1e-6:rect[2]=168.48
for name in ['VDD','VSS']:
 text=(B/'ot_s81sl_ve_s_tpl_w1728.lef').read_text();part=text.split('  PIN '+name+'\n')[1].split('  END '+name)[0]
 for a,b,c,d in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',part):
  vals=list(map(float,[a,b,c,d]))
  if vals[0]>159.84:sl['pg_obstructions_um'].setdefault('M5',[]).append(vals)
sl['note']='PRIVATE W172.8 prototype: exact2611clock homes/masters and old30810sink census retained; newG1 ALL-cell census/reprice mandatory beforeCTS. No measured newmean or production promotion.'
ms=R/'master_slice';ms.mkdir(exist_ok=True);(ms/'ot_s81sl_ve_s.json').write_text(json.dumps(sl,indent=1)+'\n')
sinks=[];reset=[];moved=[]
for line in (R/'geo.txt').read_text().splitlines():
 a=line.split()
 if a[0]!='SINK':continue
 x,y=float(a[1]),float(a[2]);name=a[4];stem=name.replace('\\','').split('[')[0].split('$_')[0];dx=8.64 if stem in ['mhh','mkk','mdd','mv','mpre_q'] else 0
 row=dict(name=name,master=a[3],old_clk_pin_um=[x,y],forecast_clk_pin_um=[x+dx,y],scope='old actual CLK-pin census + geometric forecast; not new measured cell origin')
 sinks.append(row)
 if dx:moved.append(row)
 if 'u_rst.' in name:reset.append(row)
assert len(sinks)==30810 and len(moved)==386 and len(reset)==12
(R/'clocked_cell_forecast.json').write_text(json.dumps(sinks,separators=(',',':')))
rstpin=next(p for p in pd['pins'] if p['name']=='rst_n');resetreach=min(abs(v['forecast_clk_pin_um'][0]-rstpin['x'])+abs(v['forecast_clk_pin_um'][1]-rstpin['y']) for v in reset)
receipt=dict(scope='PRIVATE prototype preparation; no production promotion or measured newmean',baseline_plan_sha256=sha(R/'baseline_plan.json'),candidate_plan_sha256=sha(R/'plan_W1728.json'),affected_types=len(rows),rows=rows,global_clock_tap_xy_changes=tapmoves,pins=488,E_pins_moved=387,forecast_E_registers_moved=386,reset_cells_kept=len(reset),reset_pin=rstpin,nearest_reset_clockpin_reach_forecast_um=resetreach,native_clock=next(p for p in pd['pins']if p['name']=='clk'),clock_nodes=len(sl['core_tree']['nodes']),old_actual_clocked_cells=30810,fresh_all_cell_census='REQUIRED after newG1; oldgeo has no combinational-cell positions',mean_status='NOT MEASURED',added_cycles=0)
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print({k:v for k,v in receipt.items() if k not in ['rows','global_clock_tap_xy_changes']});print('mingap',min(r['nearest_gap_um'] for r in rows),'mirroredclocktapupdates',len(tapmoves))
