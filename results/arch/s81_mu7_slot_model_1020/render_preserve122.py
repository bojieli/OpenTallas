from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path(__file__).parent;p=json.loads((B/'inputs/mu6_plan.json').read_text());m=json.loads((B/'preserve122_model.json').read_text());q=m['rigid_existing_array_translation_option'];fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,title,boxes,extras in [(axs[0],'Frozen mu6 source: 122 frames / 1130 ROM slots',p['blocks'],[]),(axs[1],'Preserve 122: rigid translation probe (REFUSED outline)',q['translated_boxes'],q['new_svc_and_reader_boxes'])]:
 for b in boxes+extras:
  color='#5686b0' if b['kind']=='frame' else '#d79040' if b['kind'] in ['svc','idx'] else '#b7c1c8'
  ax.add_patch(Rectangle((b['x']/1000,b['y']/1000),b['w']/1000,b['h']/1000,facecolor=color,edgecolor='white',linewidth=.3,alpha=.9))
 ax.add_patch(Rectangle((0,0),31.9685,25,fill=False,edgecolor='#b32222',linewidth=1.5));ax.axhline(25,color='#b32222',linestyle='--');ax.set_xlim(-.5,33);ax.set_ylim(-.5,30.5);ax.set_aspect('equal');ax.set_xlabel('mm');ax.set_ylabel('mm');ax.set_title(title,fontsize=10)
axs[1].text(.5,29.7,'Shift 4.3632 mm; required H 29.3632 mm\nNo data/clock/boot or new source adoption',fontsize=9,va='top',bbox=dict(facecolor='white',alpha=.85,edgecolor='none'));fig.suptitle('Model only: all 122 source frames preserved; rigid growth exceeds source outline',fontsize=12);fig.tight_layout();fig.savefig(B/'preserve122_model.png',dpi=150)
