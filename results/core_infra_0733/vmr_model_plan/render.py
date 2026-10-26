import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import core_infra as CI
p=Path('.');s=json.load(open('slice.json'));routes=json.load(open('routes.json'));tech=json.load(open('identity.json'));model=json.load(open('model_result.json'));plan=CI.compile_slice(s);fig,ax=plt.subplots(figsize=(12,12));W,H=s['outline_um'];ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='core-local x (um)',ylabel='core-local y (um)')
for line in Path('technology.tsv').read_text().splitlines():
 f=line.split()
 if f and f[0]=='OBSTACLE' and 'macro' in f:
  a=f.index('macro');x,y,X,Y=[float(v)/1000 for v in f[a+1:]];ax.add_patch(Rectangle((x-4.32,y-4.32),X-x+8.64,Y-y+8.64,fill=False,ec='#d97706',lw=1.2));ax.add_patch(Rectangle((x,y),X-x,Y-y,fc='#e5e7eb',ec='#64748b',lw=1.2));ax.text((x+X)/2,(y+Y)/2,'SRAM\nM1–M3 full OBS\nM4 OBS / M5 open',ha='center',va='center',fontsize=9,color='#475569')
colors={'M2':'#80b1d3','M3':'#80b1d3','M4':'#075985','M5':'#075985'}
for r in routes:ax.plot([r['a'][0],r['b'][0]],[r['a'][1],r['b'][1]],color=colors[r['layer']],lw=.45 if r['layer'] in ('M2','M3') else 1.2,alpha=.45 if r['layer'] in ('M2','M3') else .9)
for c in plan['cells']:
 x,y=c['xy_um'];w,h=c.get('size_um',[.6,.27]);ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc='#7c3aed' if '_entry' in c['name'] else '#dc2626',ec='none'))
for i in s['islands']:
 x,y,X,Y=i['rect_um'];ax.add_patch(Rectangle((x,y),X-x,Y-y,fill=False,ec='#16a34a',lw=2));ax.annotate('2 common BUFx24 + tree root\nseparate pure clock/reset FT ports',xy=i['centre_um'],xytext=(190,169),fontsize=8,arrowprops=dict(arrowstyle='->'))
ax.set_title('VMR MODEL ONLY — 176 legal planned cells, 4308 FF sinks, 512 same-leaf pairs\nM2/M3 default-width leaf prototype; 2W M4/M5 trunks; NO physical proposal',fontsize=12)
fig.text(.07,.035,'Post-legalization MERGED model: TT mean256.08/window19.34ps; FF192.11/18.50ps.\n0ps prototype input; actual corner pin caps; no measured sizing/padding. Declared-via R/C, coupling,\ndata/PG capacity and macro access qualification OPEN. Clock-only merged M2/M3 demand63/82 of225 nominal tracks; data/PG reservation OPEN.',fontsize=9,color='#9a3412')
fig.savefig('review.png',dpi=140,bbox_inches='tight')
