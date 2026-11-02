from pathlib import Path
import json,gzip
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;P=R/'inputs';T=json.load(open(R/'targets.json'));M=json.load(open(R/'model.json'));cells=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];by={c[0]:c for c in cells};fig=plt.figure(figsize=(16,9));grid=fig.add_gridspec(2,2,width_ratios=[1.3,1]);a=fig.add_subplot(grid[:,0]);b=fig.add_subplot(grid[0,1]);cax=fig.add_subplot(grid[1,1]);colors={'ft2_ring_band_FFs':'#087e9b','ft2_stage0':'#ba6829','ft6_stage2':'#714bb0'}
ff=[c for c in cells if c[1].startswith('DFF') and c[0]not in T];a.scatter([(c[2][0]+c[2][2])/2000 for c in ff],[(c[2][1]+c[2][3])/2000 for c in ff],s=.35,c='#a8b6bf',alpha=.6,rasterized=True,label='unchanged other FFs')
for fam,col in colors.items():
 ts=[t for t in T.values()if t['family']==fam];a.scatter([t['xy_um'][0]for t in ts],[t['xy_um'][1]for t in ts],s=2,c=col,label=f"{fam}: {len(ts)}")
# Show all five native ft6 stages and landing ring outputs as context, not new routed clock wires.
for st in range(5):
 cs=[c for c in cells if c[1].startswith('DFF')and f'u_ft_ft6_o_{st}/'in c[0]];xy=[T[c[0]]['xy_um']if c[0]in T else[(c[2][0]+c[2][2])/2000,(c[2][1]+c[2][3])/2000]for c in cs];a.scatter([p[0]for p in xy],[p[1]for p in xy],s=.6,c='#714bb0');a.text(sum(p[0]for p in xy)/len(xy)+20,sum(p[1]for p in xy)/len(xy),f'ft6 stage{st}',fontsize=8)
a.add_patch(Rectangle((17.28,935.82),110.94,25.92,fill=False,ec='#087e9b',ls='--',lw=1));a.text(145,940,'old ft2 ring band',fontsize=8,c='#087e9b');a.set(xlim=(0,1442.88),ylim=(0,1226.88),xlabel='µm',ylabel='µm');a.set_aspect('equal');a.legend(fontsize=7,loc='lower left');a.set_title('Disabled model: 3,707 existing FFs resited\nAll other 319,576 native cell/TAP footprints fixed')
for cell in cells:
 bb=[v/1000 for v in cell[2]]
 if bb[2]<=0 or bb[0]>=260 or bb[3]<=1100 or bb[1]>=1230:continue
 if cell[0]in T:continue
 color='#d3a76b'if cell[5]=='FIRM'else'#d5dce0'
 if cell[1].startswith('TAPCELL'):color='#bd9891'
 b.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc=color,ec='none',alpha=.8))
for name,t in T.items():
 if t['family']!='ft2_ring_band_FFs':continue
 bb=[v/1000 for v in t['bbox_dbu']];b.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc=colors['ft2_ring_band_FFs'],ec='none'))
for bt in json.load(open(P/'BTerms.json')):
 if bt[0].startswith('ft2_i['):
  for layer,bb in bt[4]:b.plot((bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000,'|',ms=3,c='#1998b0')
b.plot(61.536,1224.224,'r*',ms=10,label='unchanged fclk_in_ft2_i[0]');b.set(xlim=(0,260),ylim=(1100,1230),xlabel='µm',ylabel='µm');b.set_title('New ft2 ring targets avoid actual cells/TAPs\nPublic pins fixed; other FIRM bands remain in place');b.legend(fontsize=7);b.set_aspect('equal')
name=lambda st:f'u_bound.u_ft_ft6_o_{st}/q\\[471\\]$_DFF_P_';old0=by[name(1)];old1=by[name(2)];p0=[(old0[2][0]+old0[2][2])/2000,(old0[2][1]+old0[2][3])/2000];p1=[(old1[2][0]+old1[2][2])/2000,(old1[2][1]+old1[2][3])/2000];p2=T[name(2)]['xy_um'];cax.plot([p0[0],p1[0]],[p0[1],p1[1]],'--',c='#bd5c4d',lw=1,label='old 411.912 µm Manhattan hop');cax.plot([p0[0],p2[0]],[p0[1],p2[1]],'-',c='#714bb0',lw=1,label=f"new {sum(abs(x-y)for x,y in zip(p0,p2)):.3f} µm Manhattan hop");cax.plot(*p0,'o',c='black');cax.plot(*p1,'x',c='#bd5c4d');cax.plot(*p2,'o',c='#714bb0');cax.set(xlim=(830,1060),ylim=(460,745),xlabel='µm',ylabel='µm');cax.set_title('Exact ft6 q471 stage1→stage2 witness\nLines show connectivity; all five stages/cycles preserved');cax.legend(fontsize=7);cax.set_aspect('equal')
fig.suptitle('T51 DISABLED native-row/obstacle model — no source/DB changes, no CAD\nR2R max402.33 / 0>405, public pin max149.81; sparse fill, E/W flags, actual GRT4843, PG buffer opens and source/clock holds remain',fontsize=11);fig.tight_layout();fig.savefig(R/'T51_native_anchor_MODEL_LOOK.png',dpi=160)
