#!/usr/bin/env python3
"""Make one current-plan unsigned VM calendar compact proposal; never edit input."""
import argparse, copy, hashlib, json
from pathlib import Path
MOD='hfd_hgi_vm_calendar_f20'
OLD=[241.92,116.64]; NEW=[216.0,112.32]
def write(p,d): p.write_text(json.dumps(d,indent=1)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('slice',type=Path);a.add_argument('out',type=Path);x=a.parse_args();x.out.mkdir(parents=True,exist_ok=False)
 plan=json.load(open(x.plan/'die_plan.json'));cm=json.load(open(x.plan/'core_macros.json'))['cores'][MOD]
 refs=[(tn,c) for tn,t in plan['partition_types'].items() for c in t.get('hard_cores',[]) if c['module']==MOD]
 assert len(refs)==4 and len({c['pins_file'] for _,c in refs})==1
 assert all(all(abs(v-z)<1e-6 for v,z in zip(c['outline_um'],OLD)) for _,c in refs)
 pins=json.load(open(x.plan/refs[0][1]['pins_file']));out=copy.deepcopy(pins)
 for p in out:
  if abs(p['y']-(OLD[1]-.096))<1e-6:
   p['x']=round(.024+round((p['x']*(NEW[0]/OLD[0])-.024)/.048)*.048,6);p['y']=NEW[1]-.096
  if p['name'].startswith('ordinal['):p['x']=round(.024+round((p['x']*(NEW[0]/OLD[0])-.024)/.048)*.048,6)
  if p['name']=='clk':p.update(x=120.936,y=99.36,w=.048,h=.48)
 assert len({p['name'] for p in out})==len(out)==558
 assert all(0<=p['x']<=NEW[0] and 0<=p['y']<=NEW[1] for p in out)
 assert all(p==q for p,q in zip(pins,out) if p['y']<1 and p['name']!='clk' and not p['name'].startswith('ordinal['))
 # Peak per-layer per-face ten-um pin window, including original crowded S window.
 peaks={}
 for face,ps in [('N',[p for p in out if p['y']>NEW[1]-1]),('S',[p for p in out if p['y']<1]),('W',[p for p in out if p['x']<1])]:
  for layer in {p['layer'] for p in ps}:
   vs=sorted(p['x'] if face in 'NS' else p['y'] for p in ps if p['layer']==layer)
   peaks[face+'/'+layer]=max((sum(v<=w<=v+10+1e-8 for w in vs)/10 for v in vs),default=0)
 assert max(peaks.values())<=6
 sl=json.load(open(x.slice));assert sl['module']==MOD;sl['outline_um']=NEW
 def north(d):
  if isinstance(d,dict):
   if 'rect_um' in d:d['rect_um']=[round(v+(4.32 if i%2 else 0),6) for i,v in enumerate(d['rect_um'])]
   if 'centre_um' in d:d['centre_um'][1]=round(d['centre_um'][1]+4.32,6)
   if 'xy_um' in d and isinstance(d['xy_um'],list):d['xy_um'][1]=round(d['xy_um'][1]+4.32,6)
   for k,v in d.items():
    if k not in {'rect_um','centre_um','xy_um'}:north(v)
  elif isinstance(d,list):
   for v in d:north(v)
 for key in ['keepouts','islands','pushdown']:north(sl[key])
 sl['note']='Compact current native calendar proposal; SAME RTL and edges; two clock islands translated north4.32 to clear current macro4.32halo. clk actual M5 pin120.936,99.36; other three clock pins unchanged. Parent must reprice all taps and FT endpoint attachments.'
 macros=copy.deepcopy(cm['macros']);assert len(macros)==1
 for m in macros:
  r=m['rect_um'];assert r[0]>=8.64 and r[1]>=8.64 and r[2]+8.64<=NEW[0] and r[3]+8.64<=NEW[1]
 for isl in sl['islands']:
  a,b,c,d=isl['rect_um'];assert 0<=a<c<=NEW[0] and 0<=b<d<=NEW[1]
  assert all(c<=m['rect_um'][0]-4.32 or a>=m['rect_um'][2]+4.32 or d<=m['rect_um'][1]-4.32 or b>=m['rect_um'][3]+4.32 for m in macros)
 def xy(p,c,wh):
  u,v=p['x'],p['y'];ori=c.get('orient','R0');w,h=wh
  if ori in ['MY','R180']:u=w-u
  if ori in ['MX','R180']:v=h-v
  return [round(c['origin_um'][0]+u,6),round(c['origin_um'][1]+v,6)]
 delta=[]
 for tn,c in refs:
  for p,q in zip(pins,out):delta.append(dict(type=tn,inst=c['inst'],port=p['name'],old=xy(p,c,OLD),new=xy(q,c,NEW)))
 write(x.out/'pins.json',out);write(x.out/'master_slice.json',sl);write(x.out/'macros.json',macros);write(x.out/'endpoint_delta.json',delta)
 rep=dict(status='PROPOSAL_NO_PNR',module=MOD,outline_um=NEW,aspect=NEW[0]/NEW[1],replicas=4,pins=len(out),endpoint_records=len(delta),peak_pins_per_um_10um=peaks,macro_halo_um=4.32,macro_placements='Exact current core_macros, not stale earlier placement',cycles_added=0,source_change=False,clock_delta='Main clk to current shifted island centre; other clk_tgt/clk_cap/clk_mem exact. Two islands north4.32. Parent clock/reset+CA/FT event recompose required.',min_free_fill_estimate=.13*((OLD[0]-8.64)*(OLD[1]-8.64)-174.744*70.488)/((NEW[0]-8.64)*(NEW[1]-8.64)-174.744*70.488))
 write(x.out/'estimate.json',rep)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,ax=plt.subplots(figsize=(11,6));ax.add_patch(Rectangle((0,0),*NEW,fill=False))
 for m in macros:
  a,b,c,d=m['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='gray',alpha=.35));ax.add_patch(Rectangle((a-4.32,b-4.32),c-a+8.64,d-b+8.64,fill=False,linestyle='--',edgecolor='gray'))
 for i in sl['islands']:
  a,b,c,d=i['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='orange',alpha=.5))
 for layer,color in [('M4','green'),('M5','purple')]:
  ps=[p for p in out if p['layer']==layer];ax.scatter([p['x'] for p in ps],[p['y'] for p in ps],s=3,c=color,label=layer+' pins')
 for p in out:
  if p['name'].startswith('clk'):ax.plot(p['x'],p['y'],'*',markersize=11);ax.annotate(p['name'],(p['x'],p['y']),fontsize=8)
 ax.set_xlim(-5,NEW[0]+5);ax.set_ylim(-5,NEW[1]+5);ax.set_aspect('equal');ax.legend(loc='upper left',bbox_to_anchor=(1,1));ax.set_title('VM calendar216x112.32: one unchanged SRAM, full4.32halo, two clock islands,558 actual pins\nProposal only: parent FT/tap/CA recompose + actual placement required');fig.tight_layout();fig.savefig(x.out/'proposal.png',dpi=150)
 print(json.dumps(rep,sort_keys=True))
if __name__=='__main__':main()
