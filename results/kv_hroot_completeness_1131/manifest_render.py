import json,re,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geom_rules as G
R=Path(__file__).resolve().parent
D=G.Design('/srv/opentallas-scratch/claude/wt/codex-kv-physical-1101/results/kv_hroot_reloc_1131_A4_actual.tsv')
P=json.loads((R/'proposal_data_pin_reset_pending.json').read_text())
byname={c[-1]:(i,c) for i,c in D.cells.items()}
resetgraph=json.loads((R/'native_reset_source_graph.json').read_text())
leaves={}
for q,g in resetgraph.items():
 n='u_bound.'+g['path'][0]['instance']+'/q$_DFF_P_'
 assert n in byname,n
 leaves[q]=dict(name=n,xy=list(G.ctr(byname[n][1])),source_path=g)
clocks=[p for p in D.pins if re.fullmatch(r'clk(?:_t\d+)?',p['name'])]
rows=[]
for m in P['moves']:
 xy=m['new'];near=min(leaves,key=lambda q:sum(abs(a-b) for a,b in zip(leaves[q]['xy'],xy)))
 clk=min(clocks,key=lambda p:abs(p['x']-xy[0])+abs(p['y']-xy[1]))
 rows.append(dict(**m,nearest_reset_terminal=near,reset_source=leaves[near]['name'],reset_source_xy=leaves[near]['xy'],reset_reach_um=sum(abs(a-b) for a,b in zip(leaves[near]['xy'],xy)),clock_home=clk['name'],clock_xy=[clk['x'],clk['y']],clock_reach_um=abs(clk['x']-xy[0])+abs(clk['y']-xy[1])))
# Include unchanged reset endpoint violations: existing native flops need equal-depth nearest-terminal assignment too.
for p in P['residual_bad']:
 if 'u_rrl_' not in p['launch']:raise ValueError('data residual')
 n=p['capture'];xy=p['capture_xy'];near=min(leaves,key=lambda q:sum(abs(a-b) for a,b in zip(leaves[q]['xy'],xy)))
 if not any(r['name']==n for r in rows):rows.append(dict(name=n,old=xy,new=xy,move_um=0,old_reset_source=p['launch'],nearest_reset_terminal=near,reset_source=leaves[near]['name'],reset_source_xy=leaves[near]['xy'],reset_reach_um=sum(abs(a-b) for a,b in zip(leaves[near]['xy'],xy))))
out=dict(scope='UNSIGNED MODEL ONLY; original ODB unmodified; all native data and per-bit pin constraints modeled; exact reset/clock connectivity changes require ordinary native hooks and full gates',moves=rows,terminal_sources=leaves,clock_homes=clocks)
(R/'endpoint_clock_reset_manifest.json').write_text(json.dumps(out,indent=2))
print('moves',sum(x['move_um']>0 for x in rows),'reset endpoints',len(rows),'reset max',max(x['reset_reach_um'] for x in rows),'clock max',max(x.get('clock_reach_um',0) for x in rows))
fig,axs=plt.subplots(2,1,figsize=(16,14))
seq=[c for c in D.cells.values() if c[0]=='S'];x=np.array([G.ctr(c) for c in seq]);changed={r['name']:r['new'] for r in rows};y=np.array([changed.get(c[-1],G.ctr(c)) for c in seq])
for ax,a,title in zip(axs,(x,y),('A4 actual post-DPL FAIL: 348 captures >405um','Completeness PREP: 958 native FF moves; reset/clock assignment pending ordinary hooks')):
 ax.scatter(a[:,0],a[:,1],s=.3,c='#276294',alpha=.55)
 for p in D.pins:
  if p['sig']=='SIGNAL':ax.plot(p['x'],p['y'],'.',color='#27a745',ms=1)
 ax.scatter([q['xy'][0] for q in leaves.values()],[q['xy'][1] for q in leaves.values()],marker='^',s=35,c='orange',edgecolor='black',label='51 unchanged real reset terminals')
 ax.set(xlim=(0,1900.8),ylim=(0,838.08),aspect='equal',title=title,xlabel='um',ylabel='um');ax.legend(loc='upper left')
for r in rows:
 if r['move_um']>0:axs[1].plot([r['old'][0],r['new'][0]],[r['old'][1],r['new'][1]],color='#b33355',lw=.25,alpha=.25)
fig.tight_layout();fig.savefig(R/'native_endpoint_proposal.png',dpi=150)
