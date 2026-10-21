import sys,json,subprocess,hashlib,math
from pathlib import Path
r=Path(__file__).resolve().parents[4];sys.path.insert(0,str(r/'tools'));import check_macro_track_alignment as C
def get(ref,p):return subprocess.check_output(['git','-C',str(r),'show',ref+':'+p],stderr=subprocess.DEVNULL)
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);args=ap.parse_args()
p=json.load(open(args.plan));out=[];cache={}
for name,bn in [('lepw_mu','s_0S'),('lepw_mab_mu','s_0N')]:
 d=json.load(open(r/('physical/ref_tile/s81_mu72_assembly/'+name+'.json')));b=next(x for x in p['blocks']if x['name']==bn);rows=[];constraints={'x':[],'y':[]};bodies=[]
 for ch in d['children']:
  row={'instance':ch['inst'],'at':ch['at'],'view':ch.get('view'),'unqualified_standin':'standin' in ch.get('view','')}
  if not ch.get('view'):row['status']='UNBOUND_NO_ACTUAL_LEF';rows.append(row);continue
  ref=ch.get('view_ref','553741303');view=ch['view'];key=(ref,view)
  if key not in cache:
   names=get(ref,view+'/abstract.json')if False else subprocess.check_output(['git','-C',str(r),'ls-tree','-r','--name-only',ref,view]).decode().splitlines()
   lefs=[x for x in names if x.endswith('.lef')and'/provenance/'not in x]
   if len(lefs)!=1:cache[key]=None
   else:
    raw=get(ref,lefs[0]);cache[key]=(C.parse_lef(raw.decode())[0],hashlib.sha256(raw).hexdigest(),lefs[0])
  if cache[key]is None:row['status']='MISSING_OR_AMBIGUOUS_LEF';rows.append(row);continue
  m,h,path=cache[key];ori=ch.get('orient','R0');x=round((b['x']+ch['at'][0])*1000);y=round((b['y']+ch['at'][1])*1000)
  row.update(lef_sha256=h,lef=path,status='EXPORTED_PIN_CHECK',pins=C.check_placement(m,ori,x,y),size_um=[m['W']/1000,m['H']/1000],candidate_phase_check=C.check_placement(m,ori,x-64,y-8));rows.append(row)
  lx,ly=ch['at'];w,h=m['W']/1000,m['H']/1000;bodies.append((ch['inst'],lx,ly,w,h))
  for pin in m['pins']:
   if pin['use']in('POWER','GROUND'):continue
   choices={}
   for lay,rr in pin['rects']:
    if lay not in C.ASAP7_TRACKS_NM:continue
    axis='y'if C.ASAP7_LAYERS[lay][0]=='H'else'x';P,T=C.track_residues(C.ASAP7_TRACKS_NM[lay],axis);rr=C.transform_rect(rr,ori,m['W'],m['H']);center2=rr[1]+rr[3]+2*y if axis=='y'else rr[0]+rr[2]+2*x
    legal={((2*t-center2)//2)%P for t in T if (2*t-center2)%2==0}
    choices.setdefault((axis,lay,P),set()).update(legal)
   for(axis,lay,P),legal in choices.items():constraints[axis].append((P,legal))
 phase={}
 for axis,cs in constraints.items():
  period=math.lcm(*(P for P,_ in cs))if cs else 1;legal=set(range(period))
  for P,a in cs:legal={v for v in legal if v%P in a}
  phase[axis]={'period_nm':period,'legal_global_parent_delta_residues_nm':sorted(legal)}
 violations=[]
 for inst,x,y,w,h in bodies:
  if x<0 or y<0 or x+w>d['outline']['w']+.001 or y+h>d['outline']['h']+.001:violations.append({'type':'body_outside','instance':inst,'box':[x,y,w,h]})
 for i,a in enumerate(bodies):
  for bb in bodies[:i]:
   if min(a[1]+a[3],bb[1]+bb[3])-max(a[1],bb[1])>.001 and min(a[2]+a[4],bb[2]+bb[4])-max(a[2],bb[2])>.001:violations.append({'type':'body_overlap','instances':[a[0],bb[0]]})
 out.append({'parent':bn,'assembly':name,'global_origin_um':[b['x'],b['y']],'children':rows,'common_pin_phase':phase,'body_violations':violations,'scope':'All available exact553 descendant LEFs plus exact891 W replacements. Missing/unqualified standins remain explicit; no physical parent qualification.'})
(r/'results/arch/s81_die72_1021/g9_assembly/coll_w_parent_lattice.json').write_text(json.dumps(out,indent=1)+'\n')
for d in out:print(d['parent'],d['common_pin_phase'],'bodyviolations',len(d['body_violations']),'unbound',sum(c['status']!='EXPORTED_PIN_CHECK'for c in d['children']))
