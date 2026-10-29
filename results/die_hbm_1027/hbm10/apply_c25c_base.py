"""C25c base repair: use actual n4 leaf instances and clear the new provider from retained FT cells.
No route/STA or signed-view claim. Run SRC OUT; further C25c events compose on OUT.
"""
import hashlib,json,shutil,sys
from pathlib import Path
src,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
for f in src.iterdir():
 if f.is_file() and f.suffix=='.json':shutil.copy2(f,out/f.name)
shutil.copytree(src/'cores',out/'cores',dirs_exist_ok=True)
p=json.loads((out/'die_plan.json').read_text());r={'event':'C25c base','source_sha256':hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),'changes':[]}
for tn in ('q_hub_nw','q_hub_ne'):
 t=p['partition_types'][tn]
 c=next(c for c in t['hard_cores'] if c['inst']=='u_mu_fused_n4')
 assert not any(a['inst']==c['inst'] for a in t['contents'])
 t['contents'].append(dict(inst=c['inst'],module=c['module'],origin_um=c['origin_um'],outline_um=c['outline_um'],status='new',note='C25c: existing n4 hard core was missing from contents; data buses retain exact .uo/.dn binding'))
 r['changes'].append(dict(type=tn,instance=c['inst'],change='add missing contents for existing hard core',data_cycle_delta=0))
t=p['partition_types']['root'];c=next(c for c in t['hard_cores'] if c['inst']=='u_mu_fused_program');old=c['origin_um'][:];new=[734.4,5339.52];dy=new[1]-old[1];c['origin_um']=new
c['note']+=' | C25c: origin y -17.28 clears 137 retained L9x1 actual-bit sites; root/provider gap34.56um, data cycles0'
for c in t['contents']:
 if c['inst']=='u_mu_fused_program':c['origin_um']=new
for tap in t['clock']['taps']:
 if tap['name'].startswith('u_mu_fused_program.'):
  tap['xy'][1]=round(tap['xy'][1]+dy,4)
r['changes'].append({'type':'root','inst':'u_mu_fused_program','origin':[old,new],'reason':'retain all actual FT stations, move unsigned provider by2lattice rows','data_cycle_delta':0})
# Check actual per-bit FT cells, not only nominal centre-lines.
c=next(c for c in t['hard_cores'] if c['inst']=='u_mu_fused_program');x,y=c['origin_um'];w,h=c['outline_um'];hits=[]
for ft in t['ft_slots']:
 cw,ch=ft.get('bit_site_cell_um',[1.404,.27])
 for si,stage in enumerate(ft.get('bit_sites_um',[])):
  for bi,(sx,sy) in enumerate(stage):
   if x<sx+cw/2 and sx-cw/2<x+w and y<sy+ch/2 and sy-ch/2<y+h:hits.append([ft['name'],si,bi])
assert not hits,hits[:5];r['provider_ft_intersections']=len(hits)
p['note']=p.get('note','')+' | C25c base: n4 contents declared; provider clear of actual FT sites'
(out/'die_plan.json').write_text(json.dumps(p,indent=1));r['plan_sha256']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest()
(out/'c25c_base_report.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
