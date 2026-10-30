#!/usr/bin/env python3
"""Add physical-only SRAM/ROM hard-core records for exact existing native cells; never logical contents."""
import json,re,math,sys
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2] if '/results/' in str(Path(__file__).resolve()) else Path('/srv/opentallas-scratch/claude/wt/codex-qc-kits-2249')
R=ROOT/'results/qc_codex_kits_2249';base=json.loads((R/'base_plan.json').read_text());inv=json.loads((R/'macro_inventory.json').read_text());exact=json.loads((R/'macro_exact_map.json').read_text())
views={}
for master in {c['module'] for a in exact.values() for c in a}:
 for family in ['asap7_memory_macros_v2','asap7_memory_macros']:
  d=ROOT/'physical'/family/master;lef=d/(master+'.lef');lib=d/(master+'_tt.lib');ff=d/(master+'_ff.lib')
  if lef.exists() and lib.exists() and ff.exists():break
 else:raise ValueError('missing exact TT/FF macro views '+master)
 s=lef.read_text();size=[float(x) for x in re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',s).groups()]
 layers=[int(x) for x in re.findall(r'\bLAYER\s+M([1-9])\b',s)]
 views[master]={'lef':str(lef.relative_to(ROOT)),'lib':str(lib.relative_to(ROOT)),'size':size,'obs_max':'M'+str(max(layers))}
def rect_hit(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def ptbox(p,h=2):return [p[0]-h,p[1]-h,p[0]+h,p[1]+h]
def obs(t):
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
 t=base['partition_types'][tn];cc=cells(tn);pref=desires(tn,cc,t);occupied=obs(t);placed=[];fail=[]
 # Larger macros first; all candidates are ranked by displacement within their own dataflow region.
 for c in sorted(cc,key=lambda c:(-math.prod(views[c['module']]['size']),pref[c['inst']][1],pref[c['inst']][0])):
  n=c['inst'];m=c['module'];w,h=views[m]['size'];px,py,bounds=pref[n];W,H=t['outline_um'];halo=4.32
  bounds=bounds or [8.64,8.64,W-8.64,H-8.64]
  candidates=[]
  for dx in range(-60 if tn=='tt_ctlm' else -24,61 if tn=='tt_ctlm' else 25):
   for dy in range(-60 if tn=='tt_ctlm' else -24,61 if tn=='tt_ctlm' else 25):
    x=round((px+dx*4.32)/.054)*.054;y=round((py+dy*4.32)/.27)*.27
    a=[x-halo,y-halo,x+w+halo,y+h+halo]
    if a[0]<bounds[0]-1e-6 or a[1]<bounds[1]-1e-6 or a[2]>bounds[2]+1e-6 or a[3]>bounds[3]+1e-6:continue
    candidates.append((abs(dx)+abs(dy),abs(dx),abs(dy),x,y,a))
  choice=None
  for _,_,_,x,y,a in sorted(candidates):
   if any(rect_hit(a,b) for b in occupied):continue
   choice=x,y,a;break
  if choice is None:fail.append(n);continue
  x,y,a=choice;occupied.append(a);v=views[m]
  placed.append({'inst':n,'module':m,'origin_um':[round(x,6),round(y,6)],'outline_um':v['size'],'orient':'R0','halo_um':halo,'lef':v['lef'],'lib':v['lib'],'obs_max':v['obs_max'],'note':'Exact existing native SRAM/ROM physical placement only; no logical contents instance, cells, ports or cycles added.'})
 if fail:raise ValueError('No macro site '+tn+' '+str(fail))
 area=sum(math.prod(c['outline_um']) for c in placed);W,H=t['outline_um']
 report[tn]={'macros':len(placed),'macro_area_um2':round(area,3),'fraction':round(area/(W*H),5),'added_cells':0,'added_cycles':0,'max_shift_from_group_target_um':max(round(abs(c['origin_um'][0]-pref[c['inst']][0])+abs(c['origin_um'][1]-pref[c['inst']][1]),3) for c in placed)}
 t.setdefault('hard_cores',[]).extend(placed);t['core_pg_connect']=True;delta[tn]={'hard_cores':placed,'core_pg_connect':True}
(R/'macro_plan.json').write_text(json.dumps(base,indent=2)+'\n');(R/'macro_plan_delta.json').write_text(json.dumps(delta,indent=2)+'\n');(R/'macro_site_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
