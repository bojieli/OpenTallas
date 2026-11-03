import json,collections,importlib.util
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/home/ubuntu/coord/tmp/codex-xrt-compact-0414');ev=json.loads((p/'disabled_event.json').read_text());pins=json.loads((p/'proposed_signal_pins.json').read_text());old=json.loads((p/'source/pins.json').read_text());pg=json.loads((p/'projected_PG_bay.json').read_text());taps=json.loads((p/'source/native_rows_taps.json').read_text())
s=importlib.util.spec_from_file_location('g','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);d=g.Design('/home/ubuntu/coord/tmp/codex-s81-xrt-l4-2235/xrt/current_geom.tsv',memory_reach=True)
fig,axs=plt.subplots(1,3,figsize=(18,9),gridspec_kw={'width_ratios':[1.05,1.1,.85]})
colors={'M3':'#2171b5','M4':'#54278f','M5':'#238b45'}
a=axs[0];a.add_patch(Rectangle((0,0),311.04,395.28,fill=False,ec='black'));cs=list(d.cells.values());a.scatter([(c[2]+c[4])/2 for c in cs],[(c[3]+c[5])/2 for c in cs],s=.1,alpha=.2,color='slategray',rasterized=True)
for ly in colors:
 q=[z for z in old if z['layer']==ly];a.scatter([z['x'] for z in q],[z['y'] for z in q],s=.9,c=colors[ly],label=ly)
worst=json.loads(Path('/home/ubuntu/coord/tmp/codex-s81-xrt-l4-2235/xrt/reach_pairs.json').read_text())
for z in sorted(worst,key=lambda z:-z['distance_um'])[:8]:a.plot([z['launch_xy'][0],z['capture_xy'][0]],[z['launch_xy'][1],z['capture_xy'][1]],c='#cb181d',lw=.8,alpha=.5)
a.set_title('Retained actual final DB\n311.04 x 395.28; reach683.29 /1152fail');a.set(xlim=(-5,316),ylim=(-6,401));a.legend(loc='center left',fontsize=8)
a=axs[1];a.add_patch(Rectangle((0,0),216,172.8,fill=False,ec='black'));a.add_patch(Rectangle((4.32,4.32),207.36,164.16,fill=False,ec='gray',ls='--'));a.text(108,40,'No new cell placement\nPREP ONLY / DISABLED\nNo new PG or timing PASS',ha='center',va='center',fontsize=10)
for ly in colors:
 q=[z for z in pins if z['layer']==ly and z['bus']!='clk'];a.scatter([z['x'] for z in q],[z['y'] for z in q],s=1.1,c=colors[ly],label=ly)
for face in 'WENS':
 q=[z for z in pins if z['face']==face];a.text(0 if face=='W' else 216 if face=='E' else 108,86.4 if face in 'WE' else 172.8 if face=='N' else 0,f'{face}:{len(q)}',ha='right' if face=='W' else'left' if face=='E' else'center',va='center' if face in 'WE' else'bottom' if face=='N' else'top',fontsize=8)
a.scatter([108.012],[86.4],s=35,c='darkorange',marker='*');a.annotate('clk M5 (108.012,86.4)\nPG-safe driver bay; newTAP audit pending',(108.012,86.4),xytext=(108,120),ha='center',fontsize=8,arrowprops={'arrowstyle':'->','color':'darkorange'});a.set_title('Disabled coherent contract216 x172.8\nOutline max Manhattan388.8; preliminary41.8%');a.set(xlim=(-12,228),ylim=(-12,190))
a=axs[2]
for z in pg:
 r=z['rect_um'];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color=colors[z['layer']],alpha=.25,lw=0))
for z in taps['taps']:
 if 102<z['x']<114 and 80<z['y']<92:a.add_patch(Rectangle((z['x'],z['y']),.108,.270,fill=False,ec='red',lw=.8))
b=ev['clock_entry']['driver_bay_um'];a.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec='darkorange',lw=1.8));a.add_patch(Rectangle((107.988,86.16),.048,.48,fill=False,ec='black',lw=1));a.axvline(108.012,color='orange',lw=.5,ls=':');a.set(xlim=(102,114),ylim=(80,92),title='Clock bay / retained native PG projection\nNo M3/M4/M5 PG overlap; new FP mandatory')
for a in axs:a.set_aspect('equal');a.set_xlabel('um');a.set_ylabel('um');a.grid(alpha=.1)
fig.suptitle('XRT compact footprint + explicit M4-edge to M5-centre clock/pin-contract event\nAll7563signal identities/bit order/data-reset faces preserved +2standardPG exports; no RTL/frequency/cycle change',fontsize=13)
fig.tight_layout();fig.savefig(p/'disabled_compact_contract.png',dpi=160)
print('rendered',p/'disabled_compact_contract.png')
