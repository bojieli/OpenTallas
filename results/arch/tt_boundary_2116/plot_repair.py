import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
root=Path(__file__).resolve().parents[3]
fig,axs=plt.subplots(1,2,figsize=(12,7))
a=axs[0]
for name,y in [('core',0),('scale',237.6)]:
 d=json.load(open(root/f'physical/ref_tile/qfd_tt_{name}_leaf/floorplan.json'))
 a.add_patch(Rectangle((0,y),345.6,216,fill=False,color='black'))
 for m in d['blocks']:
  a.add_patch(Rectangle((m['x'],y+m['y']),m['w'],m['h'],color='purple',alpha=.25))
 a.text(290,y+105,name+'\n345.6 ×216 µm',ha='right')
 a.plot([110.316,234.444],[y if name=='scale' else y+216]*2,color='tab:blue',lw=4)
a.annotate('93-bit seam\n21.6 µm channel\n12-track pitch, PG gaps',xy=(175,226),xytext=(370,230),arrowprops={'arrowstyle':'->'},fontsize=8)
a.set_xlim(-10,545);a.set_ylim(-10,465);a.set_aspect('equal');a.set_xlabel('µm');a.set_ylabel('µm');a.set_title('Actual candidate leaves and SRAM outlines')
a=axs[1]
for x in [184.668,184.716]:a.axvline(x,color='green',ls='--')
a.plot([],[],color='green',ls='--',label='M5 track .012+n·.048')
a.add_patch(Rectangle((184.692,.054),.024,.084,fill=False,color='red',lw=2,label='fs4 original port'))
a.add_patch(Rectangle((184.704,.054),.024,.084,fill=False,color='blue',lw=2,label='+12 nm repair'))
a.set_xlim(184.65,184.75);a.set_ylim(.03,.16);a.set_aspect('equal');a.set_xlabel('X µm');a.set_ylabel('Y µm');a.set_title('tag_payload[55]: actual GRT BPin')
a.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.2));fig.suptitle('TT pin access: all 695 scale pins missed preferred track\nMeasured geometry; corrected route and native timing remain required',fontsize=12)
fig.tight_layout();fig.savefig(Path(__file__).with_name('track_repair.png'),dpi=150)
