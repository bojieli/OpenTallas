from pathlib import Path
import json,gzip,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent;d=json.loads(gzip.decompress((r/'CURRENT_ODB_STATIC.json.gz').read_bytes()));g=json.loads((r/'TYPED_GEOMETRY.json').read_text());fig,(a,b)=plt.subplots(1,2,figsize=(14,6));colors={'DFFHQNx1_ASAP7_75t_R':'#d29a37','DFFASRHQNx1_ASAP7_75t_R':'#3a78ac','DFFHQNx2_ASAP7_75t_R':'#a52c91','DFFHQNx3_ASAP7_75t_R':'#a52c91'}
for master in colors:
 rows=[x for x in d['sequential'].values() if x['master']==master];a.scatter([x['pins']['CLK']['xy'][0] for x in rows],[x['pins']['CLK']['xy'][1] for x in rows],s=1 if master.endswith('x1_ASAP7_75t_R') else 14,c=colors[master],label=f'{master.split("_ASAP")[0]}: {len(rows)}')
root=g['current_clock']['root_xy'];a.scatter(*root,s=65,c='green',marker='s',label='Existing clk boundary root');a.add_patch(Rectangle((0,0),216,138.24,fill=False));a.set_aspect('equal');a.set_xlim(-3,219);a.set_ylim(-3,141);a.set_title('All 8,994 CURRENT clock pins / actual masters\nNo physical clock taps generated yet');a.legend(fontsize=8,loc='upper right');a.set_xlabel('um');a.set_ylabel('um')
for row in g['boundary']['mapping']:
 x,y=row['pin_points'][0];xx,yy=row['register_center'];b.plot([x,xx],[y,yy],lw=.6,c='#3b729e');b.scatter([x],[y],s=6,c='#d28d2d');b.scatter([xx],[yy],s=5,c='#3b729e')
b.add_patch(Rectangle((0,0),216,138.24,fill=False));b.set_aspect('equal');b.set_xlim(-3,219);b.set_ylim(-3,141);b.set_xlabel('um');b.set_ylabel('um');b.set_title('67 actual port-to-register BUF/INV mappings\np90 7.831 um, max 9.993 um; all-pair R2R max 340.578 um')
fig.suptitle('CURRENT RECIP saved PLACE inputs for a fresh native CTS lifecycle\nSource-to-SYNTH EQ 11,074/11,074; saved PG0 106,210/0; no old graph/model transfer or CTS execution',fontsize=11);fig.tight_layout();fig.savefig(r/'current_sink_boundary_review.png',dpi=160)
