from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent;d=json.loads((p/'reset_loads.json').read_text());s=json.loads((p/'reset_site_plan.json').read_text());r=json.loads((p/'reset_legal_projection.json').read_text())
fig,ax=plt.subplots(figsize=(13,7.4));ax.add_patch(Rectangle((0,0),388.8,172.8,fill=False,color='black',lw=1.8));over=set(d['over405_names'])
for flag,col,lab,sz in [(False,'#7a9ebb','Other reset captures',9),(True,'#d1453b','486 original overreach captures',13)]:
 q=[x['xy'] for x in d['captures'] if (x['name'] in over)==flag];ax.scatter([z[0] for z in q],[z[1] for z in q],s=sz,c=col,alpha=.55,label=lab,rasterized=True)
t=r['target_xy'];pre=r['predecessor_xy'];old=d['source']['xy'];ax.scatter(*pre,c='#142a6b',marker='s',s=100,label='rst_s[0]: retained at E');ax.scatter(*old,c='#df8c16',marker='o',facecolors='none',s=140,label='Original R2 rst_s[1]');ax.scatter(*t,c='#148431',marker='*',s=260,label='Proposed existing R2 rst_s[1]')
ax.annotate('',xy=t,xytext=pre,arrowprops={'arrowstyle':'->','lw':2,'color':'#142a6b'});ax.text(227,112,'Incoming registered hop222.53um',color='#142a6b',fontsize=10)
for e in r['direct_outgoing']:ax.annotate('',xy=e['capture_xy'],xytext=t,arrowprops={'arrowstyle':'->','lw':1.4,'color':'#873e95','linestyle':'--'})
ax.text(240,70,'Existing output buffers remain near E\nLongest tree edge233.71um',color='#873e95',fontsize=10)
ax.annotate('ROW_287, MX\ncentre(167.400,81.945)\n0 overlaps; same master/cycles',xy=t,xytext=(78,118),arrowprops={'arrowstyle':'-','color':'#148431'},color='#148431',fontsize=10)
ax.text(10,178,'N face: original pins and capture FFs retained',fontsize=10);ax.text(10,-12,'S face: original pins and capture FFs retained',fontsize=10)
ax.set(xlim=(-5,400),ylim=(-16,187),xlabel='x(um)',ylabel='y(um)');ax.set_aspect('equal');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=2,fontsize=9)
ax.set_title('PROPOSED R2 zero-cycle reset delivery relocation - not applied\nOwn actual R2 DB; one existing internal FF; no new cells, ports, RTL or reset stages',fontsize=13)
fig.text(.075,.035,'Projected global r2r461.11 ->352.62um;486 ->0 captures>405. All reset captures<=254.23um from new FF.\nR2 own vacancy/site and QN->INV_093538_->D trace verified. Aspect2.25 remains; no CTS/timing/DRV waiver.',fontsize=10)
fig.subplots_adjust(bottom=.26,top=.88,left=.075,right=.98);fig.savefig(p/'planned.png',dpi=150)
