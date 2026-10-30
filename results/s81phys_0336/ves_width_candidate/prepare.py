from pathlib import Path
import json,re,copy,hashlib,sys,math
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema as S;import core_pin_sites_gate as G
B=Path(__file__).parent;oldW=164.16;newW=172.8;H=345.6;dx=8.64;src=B.parent/'unsigned_clock/parent_plan.json';raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()=='bcfcb4e1737e8140fab9c94aec6128c4a086ab5fa953e07159813abb11819d10';D=json.loads(raw);P=S.Plan(D);doc=json.load(open(B/'old_pins.json'));new=copy.deepcopy(doc);moved=[]
for p in new['pins']:
 if p['x']>oldW-.1 and p['name']!='clk':moved.append(p['name']);p['x']=round(p['x']+dx,6)
assert len(new['pins'])==488 and next(p for p in new['pins']if p['name']=='clk')==next(p for p in doc['pins']if p['name']=='clk')
new['lef']='results/s81phys_0336/ves_width_candidate/ot_s81sl_ve_s_tpl_w1728.lef';new['source']+=' | PRIVATE unsignedinternal width172.8 candidate: Eedgepins+8.64, clock/localotherpins preserved, noRTL/cyclechange; requires source/parent/nativegeometry/timing adoption';new['pinhash']=hashlib.sha256(json.dumps(new['pins'],sort_keys=True).encode()).hexdigest()[:12];(B/'ot_s81sl_ve_s_tpl_w1728.json').write_text(json.dumps(new,indent=2)+'\n')
s=(B/'old.lef').read_text();s=s.replace('SIZE 164.160 BY 345.600','SIZE 172.800 BY 345.600');assert 'SIZE 172.800' in s
# Move the exact signal rectangles belonging to the shifted canonical pin names.
for name in moved:
 pat=r'(  PIN '+re.escape(name)+r'\n)(.*?)(  END '+re.escape(name)+r'\n)';ma=re.search(pat,s,re.S);assert ma,name
 def shift(m):return f'RECT {float(m[1])+dx:.6f} {float(m[2]):.6f} {float(m[3])+dx:.6f} {float(m[4]):.6f} ;'
 body=re.sub(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',shift,ma[2]);s=s[:ma.start(2)]+body+s[ma.end(2):]
# Repeat the declared native PDN's same M5 pitch into the new empty E strip. This is a PLAN model, not a signed PG view.
pg=[]
for name in ['VDD','VSS']:
 pat=r'(  PIN '+name+r'\n)(.*?)(  END '+name+r'\n)';ma=re.search(pat,s,re.S);body=ma[2];rs=list(re.finditer(r'        RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',body));assert rs;last=rs[-1];add=''
 for step in [4.32,8.64]:add+=f'\n        RECT {float(last[1])+step:.6f} {float(last[2]):.6f} {float(last[3])+step:.6f} {float(last[4]):.6f} ;';pg.append(dict(net=name,layer='M5',rect=[float(last[1])+step,float(last[2]),float(last[3])+step,float(last[4])]))
 body=body[:last.end()]+add+body[last.end():];s=s[:ma.start(2)]+body+s[ma.end(2):]
# Extend macro OBS to the new outline, retaining exactly the old M6/M7 clock island window.
i=s.index('  OBS\n');head,obs=s[:i],s[i:]
def obs_width(m):
 a=list(map(float,m.groups()));
 if abs(a[2]-oldW)<1e-6:a[2]=newW
 return 'RECT '+' '.join(f'{v:.6f}'for v in a)+' ;'
obs=re.sub(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',obs_width,obs);s=head+obs;(B/'ot_s81sl_ve_s_tpl_w1728.lef').write_text(s)
rows=[];alltrack=True;clockpg=[];changed=0
for tn,t in D['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_s81sl_ve_s':continue
  changed+=1;c['outline_um']=[newW,H];ox,oy=c['origin_um'];tx,ty=c.get('track_offset_um',[0,0]);ox+=tx;oy+=ty;o=c.get('orient','R0');errors=[];instances=[]
  for pin in new['pins']:
   x,y=pin['x'],pin['y'];x,y={'R0':(x,y),'MX':(x,H-y),'MY':(newW-x,y),'R180':(newW-x,H-y)}[o];x+=ox;y+=oy;L=P.layers[pin['layer']];coord=x if L['dir']=='V'else y;on=abs((coord-L['offset_um'])/L['pitch_um']-round((coord-L['offset_um'])/L['pitch_um']))<1e-5
   if not on:errors.append(pin['name'])
   if pin['name']=='clk':clockpg.append(dict(type=tn,type_xy=[x,y],blocked=S.pg_blocked('M5',x)))
   for part,p in P.parts.items():
    if p['type']!=tn:continue
    xx,yy=P.to_die(part,(x,y));coord=xx if L['dir']=='V'else yy
    if abs((coord-L['offset_um'])/L['pitch_um']-round((coord-L['offset_um'])/L['pitch_um']))>=1e-5:errors.append(part+':'+pin['name'])
  rows.append(dict(type=tn,core=c['inst'],orient=o,track_errors=errors));alltrack &=not errors
assert changed==74
# An exact patch recipe, not an adopted parent plan. All other fields are unchanged by construction.
check=G.check_pins(new['pins'],newW,H);assert check['verdict']=='PASS',check
R=dict(scope='PRIVATE unsigned internalG3 candidate only; no sourceadoption orphysical launch',source_plan_sha256=hashlib.sha256(raw).hexdigest(),old_outline=[oldW,H],candidate_outline=[newW,H],old_aspect=H/oldW,candidate_aspect=2.0,pins=488,moved_Eedge_pins=len(moved),moved_names=moved,all_other_pins_and_native_clock_unchanged=True,native_clock=next(p for p in new['pins']if p['name']=='clk'),pin_site_gate=check,parent_types=changed,parent_external_ABI_outline_neighbors_unchanged=True,parent_all_pin_track_PASS=alltrack,parent_track_rows=rows,parent_clock_PG_new_conflicts=sum(p['blocked']for p in clockpg),parent_clock_PG=clockpg,PG_plan=dict(source='same native M5 periodic0.12width/0.072spacing/4.32pitch; appendtwoexistingphasepairs only in newEstrip',new_rectangles=pg,old_clock_M6M7_island_preserved=True,scope='PLAN ONLY; fresh native PDN/PGchecks required'),clock_plan=dict(scope='keep exact frozen nativeC pin82.092/172.8 and existing2611latticeclock masters/homes forprebuildmodel; repriceall actual newG1sinklocations beforeCTS, no staleclockqualification',model_only=True),added_cycles=0)
(B/'impact.json').write_text(json.dumps(R,indent=2));print({k:v for k,v in R.items()if k not in ['moved_names','parent_track_rows','parent_clock_PG','PG_plan']})
