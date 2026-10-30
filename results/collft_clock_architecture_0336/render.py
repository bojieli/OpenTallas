import json,gzip,math,collections
from pathlib import Path
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
B=Path(__file__).parent;plans=json.load(gzip.open(B/'tree_packed_actual_pins.json.gz','rt'));rows=json.load(open(B/'clock_sinks.json'));proposal=json.load(open(B/'eight_entry_proposal.json'));ports={t['name']:t['xy']for t in proposal['taps']};screen=json.load(open(B/'packed_screen.json'))
for n,r in screen['roots'].items():ports[n]=r['corners']['TT']['entry_wire_model']['public_entry_xy_um']
fig,ax=plt.subplots(figsize=(10,12));rr=[a for a in rows if a['root']=='clk'];ff=[a for a in rows if a['root']!='clk'];ax.scatter([a['xy'][0]for a in rr],[a['xy'][1]for a in rr],s=.6,c='#aaa',alpha=.4);ax.scatter([a['xy'][0]for a in ff],[a['xy'][1]for a in ff],s=.5,c='#777',alpha=.35)
metrics={};palette=plt.get_cmap('tab10')
for index,(root,sl)in enumerate(plans.items()):
 xy={n['name']:n['xy_um']for n in sl['core_tree']['nodes']};xy['port:'+sl['core_tree']['clock_port']]=ports[root];segments=[];maxleg=0;maxleaf=0
 for n in sl['core_tree']['nodes']:
  a,b=xy[n['parent']],n['xy_um'];segments.append([a,b]);maxleg=max(maxleg,sum(abs(x-y)for x,y in zip(a,b)))
 points=sl['clock_sink_points_um']
 for l in sl['core_tree']['leaves']:
  for name in l['sinks']:
   a,b=xy[l['node']],points[name];segments.append([a,b]);maxleaf=max(maxleaf,sum(abs(x-y)for x,y in zip(a,b)))
 color=palette(int(root.split('_t')[-1])if '_t'in root else 0)if root.startswith('clk')else'#777777'
 ax.add_collection(LineCollection(segments,colors=[color],linewidths=.35 if root.startswith('clk')else.15,alpha=.60 if root.startswith('clk')else.3))
 if root.startswith('clk'):
  x,y=ports[root];ax.scatter([x],[y],marker='D',s=42,c=[color],edgecolor='black',zorder=8);ax.annotate(root,(x,y),xytext=(4,8 if y<500 else-14),textcoords='offset points',fontsize=9,color=color)
 metrics[root]=dict(max_buffer_branch_L1_um=maxleg,max_own_leaf_L1_um=maxleaf)
ax.set(xlim=(0,786.24),ylim=(0,993.6),xlabel='local x (um)',ylabel='local y (um)');ax.set_aspect('equal');ax.set_title('collft FF5 — eight proposed real RCLK entries + seven unchanged FCLK owners\nMODEL ONLY: actual CLK pins and row/body-packed clock cells; no installation/STA\nRCLK related TT54.03 / FF41.53 ps at equal input phase; actual die phase remains held',fontsize=12)
ax.text(780,45,'139,359 held existing bodies\n8,436 proposed clock buffers\n63,871 TAP/endcap bodies blocked\nNo state or cycle added',ha='right',fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='#aaa'))
fig.tight_layout();fig.savefig(B/'packed_clock_proposal.png',dpi=130);(B/'branch_geometry.json').write_text(json.dumps(metrics,indent=1));print('max actual planned leaf',max(a['max_own_leaf_L1_um']for a in metrics.values()),'max branch',max(a['max_buffer_branch_L1_um']for a in metrics.values()))
