#!/usr/bin/env python3
"""Produce isolated Pstore outer access candidate without changing data pins/RTL."""
import argparse, copy, hashlib, json, re, shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
TOP='ot_hgi_sfu_programme_store_r10'
def load(p): return json.loads(p.read_text())
def dump(p,d): p.write_text(json.dumps(d,indent=2)+'\n')
def shifted_box(b): return [round(b[0]+12.96,6),b[1],round(b[2]+12.96,6),b[3]]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--macro-lef',type=Path,required=True); a=ap.parse_args()
 o=a.out; o.mkdir(parents=True,exist_ok=True); c=o/'cut';shutil.copytree(a.input,c,dirs_exist_ok=True)
 plan=load(c/'die_plan.json'); macros=load(c/'core_macros.json'); recipe=load(c/'recipe.json'); pins=load(c/'cores/pstore.json'); orig=copy.deepcopy(pins); model=load(c/'source_model.json'); views=load(c/'views.json'); ce=load(c/'clock_entries.json')
 assert plan['die']['outline_um']==[648.0,803.52]
 m=macros['cores'][TOP]; assert len(m['macros'])==44
 oldm=copy.deepcopy(m['macros']);
 for row in m['macros']: row['rect_um']=shifted_box(row['rect_um'])
 m['outline_um']=[673.92,803.52];m['basis']+=' | isolated outer-access repair: all macros +12.96X, width +25.92; internal streets unchanged'
 r=recipe[TOP]; assert len(r['clock_sites_um'])==20 and len(r['register_guides'])==51
 oldsites=copy.deepcopy(r['clock_sites_um']); oldguides=copy.deepcopy(r['register_guides'])
 r['clock_sites_um']=[[round(x+12.96,6),y] for x,y in oldsites]
 for g in r['register_guides']: g['box_um']=shifted_box(g['box_um'])
 r['source']+=' | isolated outer-access repair673.92x803.52; no source/cycle/data-pin change'
 data_before=[p for p in orig if p['name']!='clk']; edge_before={side:sum(abs(p['x']-x)<.2 for p in data_before) for side,x in [('W',0),('E',648)]}
 assert sum(p['name']=='clk' for p in pins)==1
 for pin in pins:
  if pin['name']=='clk':pin['x']=397.464;pin['y']=432
 assert [p for p in pins if p['name']!='clk']==data_before
 plan['die']['outline_um']=[673.92,803.52];pt=plan['partition_types']['isolated_pstore_trial'];pt['outline_um']=[673.92,803.52];pt['hard_cores'][0]['outline_um']=[673.92,803.52]
 plan['clock']['mesh']['core_islands'][TOP]={'rule':'isolated outer-access repair: actual current root +20 recipe driver islands, each8.64square; all shifted+12.96X','frame':'core','instances':1,'rects_um':[[393.12,427.68,401.76,436.32]]+[[round(x-4.32,6),round(y-4.32,6),round(x+4.32,6),round(y+4.32,6)] for x,y in r['clock_sites_um']]}
 ce['isolated_pstore_trial']['u_pstore'].update(xy_um=[397.464,432],driver_anchor_um=[397.44,432])
 model['previous_trial_outline_um']=model['new_outline_um'];model['new_outline_um']=[673.92,803.52]; model['new_macro_fraction']=44*96.552*69.66/(673.92*803.52);model['clock'].update(driver_anchor_um=[397.44,432],clock_pin_um=[397.464,432]);model['scope']='isolated child candidate ONLY; width requires later parent neighbor repack; no parent adoption/release/DRT credit';model['qualification']='review-before-prototype pending; actual failed GEN3 outer-access repair; no SIGNED claim'
 dump(c/'cores/pstore.json',pins); sha=hashlib.sha256((c/'cores/pstore.json').read_bytes()).hexdigest()
 for v in views['view_list']:v['outline_um']=[673.92,803.52];v['pins_sha256']=sha;v['view']=TOP+'@'+sha[:12]
 for n,d in [('die_plan.json',plan),('core_macros.json',macros),('recipe.json',recipe),('source_model.json',model),('views.json',views),('clock_entries.json',ce)]:dump(c/n,d)
 # Draw the real macro LEF signal/clock pin centers, transformed by actual orientation.
 text=a.macro_lef.read_text(); pts=[]
 for hit in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',text,re.S):
  name,body=hit.groups()
  if 'USE POWER' in body or 'USE GROUND' in body:continue
  for q in re.finditer(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body):
   x1,y1,x2,y2=map(float,q.groups());pts.append(((x1+x2)/2,(y1+y2)/2))
 assert pts
 fig,axes=plt.subplots(1,3,figsize=(16,10),gridspec_kw={'width_ratios':[3,1,1]})
 actual=[]
 for row in m['macros']:
  x,y,x2,y2=row['rect_um'];w=x2-x;h=y2-y
  for ax in axes:ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,facecolor='#fde4bd',edgecolor='none'));ax.add_patch(Rectangle((x,y),w,h,facecolor='#dbe6ed',edgecolor='#43627a',lw=.5))
  q=[]
  for px,py in pts:
   if row['orient'] in ('MY','R180'):px=w-px
   if row['orient'] in ('MX','R180'):py=h-py
   q.append((x+px,y+py))
  actual.extend(q)
 for ax in axes:
  ax.scatter(*zip(*actual),s=.22,c='#b23040');ax.add_patch(Rectangle((0,0),673.92,803.52,fill=False,edgecolor='black'));ax.set_ylim(-3,808);ax.set_aspect('equal');ax.grid(alpha=.15)
 axes[0].scatter(*zip(*r['clock_sites_um']),c='#266d32',marker='+',s=35);axes[0].scatter([397.44],[432],c='purple',marker='*',s=60)
 for g in r['register_guides']:
  x,y,x2,y2=g['box_um'];axes[0].add_patch(Rectangle((x,y),x2-x,y2-y,fill=False,edgecolor='#538d55',alpha=.25,lw=.4))
 axes[0].set_xlim(-5,679);axes[0].set_title('Isolated Pstore673.92×803.52\n44 macros,20 anchors,51 existing-stage guides shifted+12.96X')
 axes[1].set_xlim(-1,30);axes[1].set_title('Outer W macro access\n12.960µm beyond4.32halo');axes[2].set_xlim(644,675);axes[2].set_title('Outer E macro access\n13.176µm beyond4.32halo')
 fig.suptitle('Planned candidate only: red=actual LEF signal/clock pins; tan=4.32µm halo\nData pins/source/cycles unchanged. Parent source reach and neighbor repack remain HELD.',fontsize=12);fig.tight_layout();fig.savefig(o/'outer_access.png',dpi=150);plt.close(fig);shutil.copyfile(o/'outer_access.png',c/'scoped_floorplan.png')
 minx=min(q['rect_um'][0] for q in m['macros']);maxx=max(q['rect_um'][2] for q in m['macros'])
 report=dict(schema='opentallas.pstore.outer_access_delta.v1',old_outline=[648,803.52],new_outline=[673.92,803.52],shift_x_um=12.96,macros=44,anchors=20,guides=51,nonclock_pins_unchanged=len(data_before),old_boundary_nonclock_pin_counts=edge_before,macro_fraction=model['new_macro_fraction'],outer_legal_channels_um={'W':round(minx-4.32,6),'E':round(673.92-maxx-4.32,6)},internal_vertical_street_um=39.096,internal_horizontal_street_um=16.74,clock_anchor=[397.44,432],clock_pin=[397.464,432],actual_macro_lef=str(a.macro_lef),macro_pin_rect_centers_per_master=len(pts),parent_adoption=False)
 dump(o/'delta.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
