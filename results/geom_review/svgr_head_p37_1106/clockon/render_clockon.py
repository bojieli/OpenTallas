from pathlib import Path
import json,hashlib,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
K=ROOT/'kits_clockon/ot_svgr_own_2054dcac0c09-headtail_p37_clockon';f=json.loads((K/'freeze.json').read_text());pp=json.loads((K/'plan_pins.json').read_text())['pins'];cl=[p for p in pp if p['name'] in f['clocks']];w,h=f['outline_um']
fig,(a,b)=plt.subplots(1,2,figsize=(13,9),gridspec_kw={'width_ratios':[1,2]});a.add_patch(plt.Rectangle((0,0),w,h,fill=False));a.add_patch(plt.Rectangle((4.32,4.32),w-8.64,h-8.64,fill=False,color='gray',ls='--'))
for L in sorted({p['layer'] for p in pp}):
 p=[p for p in pp if p['layer']==L];a.scatter([p['x'] for p in p],[p['y'] for p in p],s=2,label=f'{L}: {len(p)}')
a.scatter([p['x'] for p in cl],[p['y'] for p in cl],s=25,marker='x',color='black');a.set_aspect('equal');a.set_xlim(-8,w+8);a.set_ylim(-5,h+5);a.legend(fontsize=8);a.set_title(f'Actual generated kit {f["kit_hash"]}\n129.6 × 432 µm, 4,897 pins')
for i in range(1341,1361):b.axvline(.024+i*.048,color='lightgray',lw=.6)
for i,p in enumerate(cl):
 b.add_patch(plt.Rectangle((p['x']-.024,p['y']-.24),.048,.48,facecolor=f'C{i}',alpha=.6));b.plot(p['x'],p['y'],'k+');b.text(p['x'],216.28,p['name'],rotation=65,fontsize=9,ha='left');b.text(p['x'],215.7,f'{p["x"]:.3f}',rotation=45,fontsize=8,ha='right')
b.plot(64.8,216,'r*',ms=12,label='Coarse entry (64.8, 216), expanded on M5 grid');b.set_xlim(64.5,65.3);b.set_ylim(215.5,216.75);b.set_aspect('equal');b.set_title('All six scalar clock pins: 0.096 µm spacing\nM5 tracks: offset 0.024 µm / pitch 0.048 µm');b.legend(loc='lower left',fontsize=8);b.set_xlabel('Core-frame x (µm)');b.set_ylabel('Core-frame y (µm)');fig.tight_layout();fig.savefig(ROOT/'actual_clockon.png',dpi=160)
(ROOT/'actual_clockon.json').write_text(json.dumps(dict(kit=str(K),kit_hash=f['kit_hash'],view=f['view'],outline_um=f['outline_um'],clocks=cl,clock_pin_entry='on',m5_offset_um=.024,m5_pitch_um=.048,all_clock_x_on_grid=all(abs((p['x']-.024)/.048-round((p['x']-.024)/.048))<1e-8 for p in cl),physical_route_run=False),indent=2)+'\n')
print((ROOT/'actual_clockon.json').read_text())
