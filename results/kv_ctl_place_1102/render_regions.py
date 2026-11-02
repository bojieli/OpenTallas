import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
O=Path(__file__).parent;r=json.load(open(O/'launch_regions.json'));review=json.load(open(O.parent/'geom_review/ctl_production_1101/review.json'))
bw=next(x for x in r['rows'] if 'bw_p_reg' in x['launch']);internal=next(x for x in r['rows'] if 'u_dcfg.d_q' in x['launch'] and '[43' in x['launch'].replace('\\',''))
fig,axs=plt.subplots(1,2,figsize=(13,6))
for ax,row in zip(axs,[bw,internal]):
 ax.add_patch(Rectangle((0,0),371.52,371.52,fill=False,color='black'))
 for b in review['blocks']:ax.add_patch(Rectangle((b['x'],b['y']),52.296,39.96,facecolor='#ccc',alpha=.5))
 ax.plot(*row['old_xy'],'rx',ms=9,label='Actual launch FF')
 for cap in row['capture_endpoints']:ax.plot(*cap['xy'],'.',color='#777',ms=1,alpha=.35)
 if row['public_anchors']:
  p=row['public_anchors'][0];x,y=p['xy'];ax.add_patch(Polygon([(x+150,y),(x,y+150),(x-150,y),(x,y-150)],fc='#4da3d4',alpha=.25,ec='blue',label='Public capture150um'))
  cap=next(c for c in row['capture_endpoints'] if 'o_hroot_ES' in c['name'] and '[540' in c['name'].replace('\\',''));x,y=cap['xy'];ax.plot(x,y,'ko',ms=5,label='Actual ES540 capture')
  ax.add_patch(Polygon([(x+405,y),(x,y+405),(x-405,y),(x,y-405)],fc='#dd8a38',alpha=.2,ec='#c76c16',label='Capture405um'))
  ax.set_title('Public bw_p_reg[0]: launch-only region EMPTY\n65.913um contradiction in x-y bounds')
 else:
  ax.add_patch(Polygon(row['feasible_polygon'],fc='#6fbd8b',alpha=.4,ec='green',label='Exact feasible launch polygon'))
  ax.plot(195,185,'g*',ms=12,label='Central corridor candidate')
  ax.set_title('Internal d_cfg.d_q[43]: nonempty region\n0cycle move geometrically possible; incoming/legalization open')
 ax.set(xlim=(-5,376),ylim=(-5,376),aspect='equal',xlabel='x (um)',ylabel='y (um)');ax.legend(fontsize=7,loc='lower left')
fig.suptitle('CTL actual PLACE failure: all reachable captures + public150 +405um reach constraints\n247/304 launch-only regions feasible;57 public launch-only regions empty. No RTL/cycle/physical change.',fontsize=11)
fig.tight_layout();fig.savefig(O/'reach_regions.png',dpi=140)
