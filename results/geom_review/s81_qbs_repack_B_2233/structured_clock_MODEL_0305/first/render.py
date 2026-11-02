from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;P=Path('/srv/opentallas-scratch/claude/codex-hist-postplace-0246');ns=json.load(open(R/'nodes.json'));ws=json.load(open(R/'wires.json'));ps=json.load(open(P/'actual_clock_pins.json'));ms=json.load(open(P/'post_place_snapshot.json'))['macros'];fig,(ax,z)=plt.subplots(1,2,figsize=(14,8),gridspec_kw={'width_ratios':[1.5,1]})
for m in ms:
 b=[v/1000 for v in m['bbox_dbu']];ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],fc='#d8bc8b',ec='#775a2f',lw=.5))
a=[p for p in ps if not p['macro']];ax.scatter([p['xy_dbu'][0]/1000 for p in a],[p['xy_dbu'][1]/1000 for p in a],s=.3,color='#7b9bb8',alpha=.5,rasterized=True,label='31847 unchanged FF clock pins')
a=[p for p in ps if p['macro']];ax.scatter([p['xy_dbu'][0]/1000 for p in a],[p['xy_dbu'][1]/1000 for p in a],s=14,marker='s',color='black',label='32 actual macro clock pins')
for w in ws:
 if w['visibility_route']:
  a=w['visibility_route'];ax.plot([x[0]for x in a],[x[1]for x in a],lw=.55,c='#4a8a51',alpha=.65)
for n in ns:
 ax.plot(*n['xy'],'o',ms=2,c='#228337')
 if n['kind']in('entry','root_fanout'):
  b=[v/1000 for v in n['bbox_dbu']];z.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],fc='#93c991',ec='green',lw=.7));z.text((b[0]+b[2])/2,b[1]+.135,n['name'].replace('branch_',''),fontsize=7,ha='center',va='center')
b=[321.84,328.32,326.16,332.64];ax.add_patch(Rectangle(b[:2],4.32,4.32,fill=False,ec='green'));z.add_patch(Rectangle(b[:2],4.32,4.32,fill=False,ec='green',lw=2));z.plot(324.012,331.212,'r+',ms=10,label='unchanged native M5 ck')
ax.set_xlim(0,648);ax.set_ylim(0,648);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='lower left',fontsize=7);ax.set_title('285 buffer-slot forecast /44 FF regions +32 macro singleton leaves\nAll actual cells/macros/TAPs/FFs remain fixed; no implementation emitted')
z.set_xlim(320.8,327.2);z.set_ylim(327.4,333.6);z.set_aspect('equal');z.set_xlabel('um');z.set_ylabel('um');z.legend(fontsize=7);z.set_title('Native empty4.32um entry bay fits five BUF24 forecast cells\nSites are native row/site legal; clock-wire/pin escape remains planned')
fig.suptitle('DISABLED hist structured-clock FIRST MODEL — ELECTRICAL FAIL/UNQUALIFIED\n282TT/281FF nets below BUF24 minimum characterized load. No clamp/waiver/CTS/GRT/target change.',fontsize=11);fig.tight_layout();fig.savefig(R/'clock_model_first_LOOK.png',dpi=160)
