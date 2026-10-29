#!/usr/bin/env python3
"""Logical register-bit guides, not mapped-cell placement constraints."""
import csv,json,pathlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=pathlib.Path(__file__).resolve().parent
m=json.loads((p/'model_and_guides.json').read_text())
rows=[]
def group(stage,banks,rect):
 names=[]
 for b in banks:
  names += [(f'g_write_pipe.we{stage}[{b}]',b,'WE')]
  names += [(f'g_write_pipe.wa{stage}[{b*6+i}]',b,'ADDR') for i in range(6)]
  names += [(f'g_write_pipe.wd{stage}[{b*512+i}]',b,'DATA') for i in range(512)]
 for i,(name,b,kind) in enumerate(names):
  x=round(rect[0]+(i%27)*1.44,6);y=round(rect[1]+(i//27)*.432,6)
  assert x+1.404<=rect[2]+1e-6 and y+.27<=rect[3]+1e-6
  rows.append(dict(register=name,stage=stage,bank=b,kind=kind,x_um=x,y_um=y,width_um=1.404,height_um=.27))
for g in m['new_register_guides']:group(g['stage'],g['banks'],g['rect_um'])
assert len(rows)==8304 and len({r['register'] for r in rows})==8304
with (p/'logical_bit_guides.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(10,8))
ax.add_patch(Rectangle((0,0),650.16,500.04,fill=False,color='black'))
for macro in json.loads((p/'mp.json').read_text())['macro_placement']:
 x,y=macro['origin_um'];ax.add_patch(Rectangle((x,y),171.288,70.992,color='gray',alpha=.3));ax.text(x+5,y+35,macro['k'],fontsize=7)
for island in json.loads((p/'slice.json').read_text()).get('islands',[]):
 x,y,x1,y1=island['rect_um'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,color='red',alpha=.5))
for g in m['new_register_guides']:
 x,y,x1,y1=g['rect_um'];col='tab:blue' if g['stage']==0 else 'tab:orange'
 ax.add_patch(Rectangle((x,y),x1-x,y1-y,color=col,alpha=.4));ax.text(x1+3,y+3,f"S{g['stage']} banks{g['banks']}",fontsize=8)
x,y,x1,y1=m['native_line_r_guide']['rect_um'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,color='green',alpha=.4));ax.text(x1+3,y+3,'existing line_r',fontsize=8)
for r in rows[::12]:ax.plot(r['x_um'],r['y_um'],'.',color='black',ms=.5)
ax.set(xlim=(-10,660),ylim=(-10,510),aspect='equal',xlabel='local x (um)',ylabel='local y (um)',title='TOPK opt-in 2-stage write pipeline — logical register guides\n8304 FF upper bound; source stages only, no mapped STA/P&R approval')
fig.savefig(p/'write_pipeline_guides.png',dpi=160,bbox_inches='tight')
