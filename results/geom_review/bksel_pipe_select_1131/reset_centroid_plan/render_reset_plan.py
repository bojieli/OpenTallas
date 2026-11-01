from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent;d=json.loads((p/'reset_loads.json').read_text());s=json.loads((p/'reset_site_plan.json').read_text());r=json.loads((p/'reset_legal_projection.json').read_text())
over=set(d['over405_names']);allp=d['captures'];fig,ax=plt.subplots(figsize=(13,7.4));ax.add_patch(Rectangle((0,0),388.8,172.8,fill=False,color='black',lw=1.8))
for flag,col,lab,sz in [(False,'#7a9ebb','Other reset captures',9),(True,'#d1453b','680 original overreach captures',13)]:
 q=[x['xy'] for x in allp if (x['name'] in over)==flag];ax.scatter([z[0] for z in q],[z[1] for z in q],s=sz,c=col,alpha=.55,label=lab,rasterized=True)
t=r['target_xy'];pre=r['predecessor_xy'];old=d['source']['xy'];ax.scatter(*pre,c='#142a6b',marker='s',s=100,label='rst_s[0]: retained at E');ax.scatter(*old,c='#df8c16',marker='o',facecolors='none',s=140,label='Original rst_s[1] position');ax.scatter(*t,c='#148431',marker='*',s=260,label='Proposed rst_s[1]: existing FF')
ax.annotate('',xy=t,xytext=pre,arrowprops={'arrowstyle':'->','lw':2,'color':'#142a6b'});ax.text(244,112,'Incoming registered hop 238.79 um',color='#142a6b',fontsize=10)
for e in r['direct_outgoing']:
 ax.annotate('',xy=e['capture_xy'],xytext=t,arrowprops={'arrowstyle':'->','lw':1.4,'color':'#873e95','linestyle':'--'})
ax.text(238,75,'Existing output buffers remain near E\nLongest physical tree edge 217.03 um',color='#873e95',fontsize=10)
ax.annotate('ROW_291, MX\ncentre (168.210, 83.025)\n0 overlaps; same master/cycles',xy=t,xytext=(84,116),arrowprops={'arrowstyle':'-','color':'#148431'},color='#148431',fontsize=10)
ax.text(10,178,'N face: original pins and capture FFs retained',fontsize=10);ax.text(10,-12,'S face: original pins and capture FFs retained',fontsize=10)
ax.set(xlim=(-5,400),ylim=(-16,187),xlabel='x (um)',ylabel='y (um)');ax.set_aspect('equal');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=2,fontsize=9)
ax.set_title('PROPOSED zero-cycle reset delivery relocation — not applied\nOne existing internal FF; no new cells, ports, source or clock/reset stages',fontsize=13)
fig.text(.075,.035,'Projection: global r2r 479.25 → 353.75 um; 680 → 0 captures >405. All reset captures ≤254.50 um from new FF.\nPin p90/max remain 9.09/32.93 um. Channel estimate 0.64 is still held; official EQ and measured corrected geometry required.',fontsize=10)
fig.subplots_adjust(bottom=.26,top=.88,left=.075,right=.98)
out=p;fig.savefig(out/'planned.png',dpi=160);fig.savefig(out/'planned.svg')
