from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;o=json.load(open(p/'layout_inputs.json'))
fig,(a,b)=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.5,1]})
w,h=o['outline_um'];a.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for m in o['macros']:
 a.add_patch(Rectangle((m['x'],m['y']),m['w'],m['h'],facecolor='#e2e8f0',edgecolor='#475569'))
 a.text(m['x']+m['w']/2,m['y']+m['h']/2,m['inst']+'\n'+m['orient'],ha='center',va='center',fontsize=9)
for c in o['clock_pins']:
 live=c['bit'] in [0,3,4,5,6]
 a.scatter([c['x']],[c['y']],s=40,c='#16a34a' if live else '#94a3b8',marker='+')
 a.annotate('ck[%d]'%c['bit'],(c['x'],c['y']),xytext=(3,4),textcoords='offset points',fontsize=7)
a.set_aspect('equal');a.set_xlim(-8,w+8);a.set_ylim(-8,h+8);a.set_xlabel('um');a.set_ylabel('um');a.set_title('Actual unchanged macro sites and clock-pin geometry')
b.axis('off');b.text(0,1,'Disabled NF2 capture variant',va='top',fontsize=13,weight='bold')
b.text(0,.90,'Exact composite source proof: 6370/6370\nOriginal failed record preserved.\n\nFault bank: 5 -> 21 source/mapped FF\n+16 same-edge captures, 0 cycles\nNative fault-bank count confirmed 21.\nSame original ck[0] clock role.\n\nNo new macro, pin ABI or outline.\nNo physical FF locations claimed.\n\nOne fresh SYNTH preview only:\nRTL/SDC/SELRANGE/adder gates PASS\nRaw + ODB boundary 623/623 PASS\n5 real child macros retained.\n\nTiming, CTS load/latency, child clock\nexpansion and release qualification\nremain unmeasured/held.',va='top',fontsize=10,linespacing=1.5)
fig.tight_layout();fig.savefig(p/'nf2_disabled_geometry_clock_preview.png',dpi=160)
