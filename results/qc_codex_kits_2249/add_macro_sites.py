#!/usr/bin/env python3
"""Add physical-only SRAM/ROM hard-core records for exact existing native cells; never logical contents."""
import json,re,math,sys
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2] if '/results/' in str(Path(__file__).resolve()) else Path('/srv/opentallas-scratch/claude/wt/codex-qc-kits-2249')
R=ROOT/'results/qc_codex_kits_2249';base=json.loads((R/'base_plan.json').read_text());inv=json.loads((R/'macro_inventory.json').read_text());exact=json.loads((R/'macro_exact_map.json').read_text())
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S,check as C,gen_phys as GP
P=S.Plan(base,path=R/'base_plan.json')
(R/'macro_pins').mkdir(exist_ok=True)
views={}
for master in {c['module'] for a in exact.values() for c in a}:
 for family in ['asap7_memory_macros_v2','asap7_memory_macros']:
  d=ROOT/'physical'/family/master;lef=d/(master+'.lef');lib=d/(master+'_tt.lib');ff=d/(master+'_ff.lib')
  if lef.exists() and lib.exists() and ff.exists():break
 else:raise ValueError('missing exact TT/FF macro views '+master)
 s=lef.read_text();size=[float(x) for x in re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',s).groups()]
 layers=[int(x) for x in re.findall(r'\bLAYER\s+M([1-9])\b',s)]
 # Individual LEF pin rectangles, retaining every signal/clock bit.
 pins=[];cur=None;layer=None;use='SIGNAL'
 for line in s.splitlines():
  z=line.strip();mt=re.match(r'PIN\s+(\S+)',z)
  if mt:cur=mt[1];layer=None;use='SIGNAL';continue
  if cur is None:continue
  if z=='END '+cur:cur=None;continue
  if z.startswith('USE '):use=z.split()[1]
  mt=re.match(r'LAYER\s+(M[1-9])',z)
  if mt:layer=mt[1]
  mt=re.match(r'RECT\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)',z)
  if mt and layer and use not in ('POWER','GROUND') and not any(q['name']==cur for q in pins):pins.append({'name':cur,'layer':layer,'rect':[float(q) for q in mt.groups()]})
 shifts=[]
 for axis,direction in [(0,'V'),(1,'H')]:
  a=[q for q in pins if P.layers.get(q['layer'],{}).get('dir')==direction];choices=[]
  for ii in range(-24,25):
   shift=ii*.006;minimum=1e9;ok=True
   for q in a:
    L=P.layers[q['layer']];lo,hi=q['rect'][axis],q['rect'][axis+2];mid=(lo+hi)/2+shift;v=L['offset_um']+round((mid-L['offset_um'])/L['pitch_um'])*L['pitch_um'];margin=min(v-shift-lo,hi-(v-shift))
    if margin<1e-7:ok=False;break
    minimum=min(minimum,margin)
   if ok:choices.append((-round(minimum,6) if a else 0,abs(shift),shift))
  if not choices:raise ValueError('no common legal pin phase '+master+' axis'+str(axis))
  shifts.append(min(choices)[2])
 pp=[]
 for q in pins:
  L=P.layers[q['layer']];a=0 if L['dir']=='V' else 1;pt=[(q['rect'][i]+q['rect'][i+2])/2 for i in [0,1]];pt[a]=L['offset_um']+round((pt[a]+shifts[a]-L['offset_um'])/L['pitch_um'])*L['pitch_um']-shifts[a];pp.append({'name':q['name'],'layer':q['layer'],'x':round(pt[0],6),'y':round(pt[1],6)})
 (R/'macro_pins'/(master+'.json')).write_text(json.dumps({'module':master,'pins':pp},indent=1)+'\n')
 views[master]={'offset':shifts,'pins_file':'macro_pins/'+master+'.json','lef':str(lef.relative_to(ROOT)),'lib':str(lib.relative_to(ROOT)),'size':size,'obs_max':'M'+str(max(layers))}
def rect_hit(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def ptbox(p,h=2):return [p[0]-h,p[1]-h,p[0]+h,p[1]+h]
def obs(t,tn):
 o=[]
 for b in t.get('clock',{}).get('landing_contract',{}).get('bands',{}).values():o.append(b['rect_um'])
 ck=t.get('clock',{});o += [ptbox(z['xy']) for z in ck.get('taps',[]) if 'xy'in z]
 for key in ['tap_um']:
  if ck.get(key):o.append(ptbox(ck[key]))
 for tree in ['collector_tree']:
  for r in ck.get('landing_contract',{}).get(tree,{}).get('relays',[]):o.append(ptbox(r['xy'],1))
 for key in ['ft_slots','internal_stations']:
  for f in t.get(key,[]):
   for p in f.get('regs_um',[]):o.append(ptbox(p,1.5))
   for row in f.get('bit_sites_um',[]):
    for p in row:o.append([p[0],p[1],p[0]+1.404,p[1]+.27])
 # Reserve actual implicit bit station geometry using the same generator as G0.
 pins=defaultdict(dict)
 for bus,bit,layer,x,y,face in GP.type_pins(P,tn):pins[bus][bit]=(x,y,face)
 for f in t.get('ft_slots',[]):
  groups=defaultdict(list);pi=pins[f['name']+'_i'];po=pins[f['name']+'_o'];st=int(f.get('stations',1))
  for bit in sorted(set(pi)|set(po)):
   ap=pi.get(bit)or po[bit];bp=po.get(bit)or pi[bit]
   def inset(q):
    x,y,face=q;return {'E':(x-1,y),'W':(x+1,y),'N':(x,y-1),'S':(x,y+1)}[face]
   a,b=inset(ap),inset(bp);rt=C.zroute(a,b,ap[2],bp[2]);length=C.plen(rt)
   for ii in range(st):
    if f.get('bit_sites_um') and ii>0:x,y=f['bit_sites_um'][ii-1][bit]
    else:x,y=a if f.get('bit_sites_um') else tuple(f['regs_um'][ii]) if f.get('regs_um') else C.point_at(rt,length*ii/st)
    groups[ii].append((x,y))
  for a in groups.values():o.append([min(q[0] for q in a)-1,min(q[1] for q in a)-1,max(q[0] for q in a)+1,max(q[1] for q in a)+1])
 return o

def cells(tn):
 ref=('sle_st_a_v2' if '_st_a_' in tn else 'sle_st_b_v1') if tn.startswith(('sle_st_','slw_st_')) else tn
 raw=exact[ref];by={c['inst']:c for c in raw};names=[x.split('/',1)[1] for x in inv[tn]['instances']]
 if set(names)!=set(by):raise ValueError('native instance identity mismatch '+tn)
 cc=[by[n] for n in names]
 if Counter(c['module'] for c in cc)!=Counter(inv[tn]['macros']):raise ValueError('macro count mismatch '+tn)
 return cc

def desires(tn,cc,t):
 W,H=t['outline_um'];ret={};counters=defaultdict(int)
 if tn.startswith(('sle_st_','slw_st_')):
  for c in sorted(cc,key=lambda c:c['inst']):
   n=c['inst'];m=c['module'];r=re.search(r'\.u_u_r([0-7])\.',n)
   if r:
    k=int(r[1])%4;i=counters[k];counters[k]+=1;cx=264+(i%3)*43.2;cy=(k+.5)*H/4-26+(i//3)*30.24;ret[n]=(cx,cy,None)
   else:
    k=int(re.search(r'g_btb\[(\d+)\]',n)[1]);ret[n]=(453.6,(k+.5)*H/4-20.52,None)
 elif tn in ('coll_s','coll_n','coll_core'):
  groups=defaultdict(list);extras=[]
  for c in cc:
   n=c['inst'];g=re.search(r'(.*(?:g_face_\d+_u_face|u_core))(?:\.|$)',n)
   if g and ('.u_rx.'in n or '.u_tx.'in n or '.g_codec.'in n):groups[g[1]].append(c)
   else:extras.append(c)
  contents=[c for c in t['contents'] if c.get('origin_um') and c.get('outline_um')]
  for k,(g,a) in enumerate(sorted(groups.items())):
   box=contents[k];x,y=box['origin_um'];w,h=box['outline_um'];bounds=[x,y,x+w,y+h]
   for i,c in enumerate(sorted(a,key=lambda c:(0 if '.u_rx.'in c['inst'] or '.u_tx.'in c['inst'] else 1,c['inst']))):
    ret[c['inst']]=(x+56.16+(i%2)*198.72,y+43.2+(i//2)*97.2,bounds)
  large=sorted([c for c in extras if 'g_sring'not in c['inst']],key=lambda c:c['inst'])
  small=sorted([c for c in extras if 'g_sring'in c['inst']],key=lambda c:c['inst'])
  for i,c in enumerate(large):ret[c['inst']]=(43.2+(i%2)*198.72,907.2+(i//2)*110.16,None)
  for i,c in enumerate(small):ret[c['inst']]=(453.6,889.92+i*49.68,None)
 elif '_stm_' in tn:
  for i,c in enumerate(sorted(cc,key=lambda c:c['inst'])):ret[c['inst']]=(W/2-145+(i%2)*146.88,H/2-78.84+(i//2)*95.04,None)
 elif tn=='glue':
  for i,c in enumerate(sorted(cc,key=lambda c:c['inst'])):
   if c['module'].startswith('ot_rom'):ret[c['inst']]=(302.4+counters['rom']*51.84,414.72,None);counters['rom']+=1
   else:ret[c['inst']]=(302.4,1058.4,None)
 elif tn=='tt_ctlm':
  big=[c for c in cc if c['module']=='ot_sram_1r1w_64x512_m1_r2c2'];rombig=[c for c in cc if c['module']=='ot_rom_4096x266_m8'];romsmall=[c for c in cc if c['module']=='ot_rom_4096x72_m8'];small=[c for c in cc if c['module']=='ot_sram_1r1w_32x128_m1']
  for i,c in enumerate(sorted(big,key=lambda c:c['inst'])):ret[c['inst']]=(17.28+(i%2)*190.08,86.4+(i//2)*99.36,None)
  for i,c in enumerate(sorted(rombig,key=lambda c:c['inst'])):ret[c['inst']]=(421.2+i*138.24,82.08,None)
  for i,c in enumerate(sorted(romsmall,key=lambda c:c['inst'])):ret[c['inst']]=(421.2+i*60.48,181.44,None)
  for i,c in enumerate(sorted(small,key=lambda c:c['inst'])):ret[c['inst']]=(421.2+(i%3)*77.76,293.76+(i//3)*77.76,None)
 else:raise ValueError(tn)
 assert set(ret)=={c['inst'] for c in cc}
 return ret

report={};delta={}
for tn in sorted(inv):
 t=base['partition_types'][tn];cc=cells(tn);pref=desires(tn,cc,t);occupied=obs(t,tn);placed=[];fail=[]
 # Larger macros first; all candidates are ranked by displacement within their own dataflow region.
 for c in sorted(cc,key=lambda c:(-math.prod(views[c['module']]['size']),pref[c['inst']][1],pref[c['inst']][0])):
  n=c['inst'];m=c['module'];w,h=views[m]['size'];px,py,bounds=pref[n];W,H=t['outline_um'];halo=4.32
  bounds=bounds or [8.64,8.64,W-8.64,H-8.64]
  candidates=[]
  for dx in range(-60 if tn=='tt_ctlm' else -24,61 if tn=='tt_ctlm' else 25):
   for dy in range(-60 if tn=='tt_ctlm' else -24,61 if tn=='tt_ctlm' else 25):
    x=round((px+dx*8.64)/8.64)*8.64+views[m]['offset'][0];y=round((py+dy*8.64)/8.64)*8.64+views[m]['offset'][1]
    a=[x-halo,y-halo,x+w+halo,y+h+halo]
    if a[0]<bounds[0]-1e-6 or a[1]<bounds[1]-1e-6 or a[2]>bounds[2]+1e-6 or a[3]>bounds[3]+1e-6:continue
    candidates.append((abs(dx)+abs(dy),abs(dx),abs(dy),x,y,a))
  choice=None
  for _,_,_,x,y,a in sorted(candidates):
   if any(rect_hit(a,b) for b in occupied):continue
   choice=x,y,a;break
  if choice is None:fail.append(n);continue
  x,y,a=choice;occupied.append(a);v=views[m]
  placed.append({'inst':n,'module':m,'origin_um':[round(x-views[m]['offset'][0],6),round(y-views[m]['offset'][1],6)],'track_offset_um':[round(q,6) for q in views[m]['offset']],'pins_file':views[m]['pins_file'],'outline_um':v['size'],'orient':'R0','halo_um':halo,'lef':v['lef'],'lib':v['lib'],'obs_max':v['obs_max'],'note':'Exact existing native SRAM/ROM physical placement only; no logical contents instance, cells, ports or cycles added.'})
 if fail:raise ValueError('No macro site '+tn+' '+str(fail))
 area=sum(math.prod(c['outline_um']) for c in placed);W,H=t['outline_um']
 report[tn]={'macros':len(placed),'macro_area_um2':round(area,3),'fraction':round(area/(W*H),5),'added_cells':0,'added_cycles':0,'max_shift_from_group_target_um':max(round(abs(c['origin_um'][0]-pref[c['inst']][0])+abs(c['origin_um'][1]-pref[c['inst']][1]),3) for c in placed)}
 t.setdefault('hard_cores',[]).extend(placed);t['core_pg_connect']=True;delta[tn]={'hard_cores':placed,'core_pg_connect':True}
(R/'macro_plan.json').write_text(json.dumps(base,indent=2)+'\n');(R/'macro_plan_delta.json').write_text(json.dumps(delta,indent=2)+'\n');(R/'macro_site_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
