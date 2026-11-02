from pathlib import Path
import json,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'fresh_fp_pre_constraints.json'));F=json.load(open(P/'native_anchored.odb.post_coords.json'));faces={r['name']for r in json.load(open(P/'actualFP_allFF_target_recipe.json'))['targets']if r['fixed_face']};norm=lambda s:s.replace('\\','');ck=next(r for r in C['controls']if r['name']=='ck')['boxes'][0]['bbox_dbu'];bay=[321.84,328.32,326.16,332.64];fig,(ax,z)=plt.subplots(1,2,figsize=(15,8),gridspec_kw=dict(width_ratios=[1.4,1]))
for m in C['macros']:
 b=[v/1000 for v in m['bbox_dbu']];ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#dfc298',edgecolor='#604222',lw=.7))
for group,color,size in((False,'#1768ad',.8),(True,'black',1.2)):
 ff=[f for f in F if(norm(f['name'])in faces)==group];x=[(r['bbox_dbu'][0]+r['bbox_dbu'][2])/2000 for r in ff];y=[(r['bbox_dbu'][1]+r['bbox_dbu'][3])/2000 for r in ff];ax.scatter(x,y,s=size,c=color,rasterized=True,label='1801 fixed data/reset faces'if group else'actual movable FF anchors')
ax.add_patch(Rectangle(bay[:2],bay[2]-bay[0],bay[3]-bay[1],facecolor='#82df99',edgecolor='green'));ax.annotate('actual M5 ck + empty driver bay',xy=(324.012,331.212),xytext=(130,344),color='green',arrowprops=dict(arrowstyle='->',color='green'));ax.set_xlim(0,648);ax.set_ylim(0,648);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='lower right',fontsize=8);ax.set_title('Actual anchored new FP: all31,847 FIRM/dont_touch\n0 FF/macro hops >405um; all36,809 native TAPs retained')
view=[318,325,330,337]
for p in C['PG_rects']:
 b=[v/1000 for v in p['bbox_dbu']]
 if b[0]>view[2]or b[2]<view[0]or b[1]>view[3]or b[3]<view[1]:continue
 z.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#ed8b73'if p['net']=='VDD'else'#8baedc',edgecolor='none',alpha=.65 if p['layer']=='M5'else.25))
for f in F:
 b=[v/1000 for v in f['bbox_dbu']]
 if b[0]>view[2]or b[2]<view[0]or b[1]>view[3]or b[3]<view[1]:continue
 z.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#b7c9d9',edgecolor='#23629a',lw=.3,alpha=.8))
z.add_patch(Rectangle(bay[:2],bay[2]-bay[0],bay[3]-bay[1],fill=False,edgecolor='green',lw=1.5,linestyle='--'));b=[v/1000 for v in ck];z.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#0aa13f',edgecolor='green',lw=1));z.annotate('M5 ck 48×480nm',xy=(324.012,331.212),xytext=(325,333.4),color='green',arrowprops=dict(arrowstyle='->',color='green'));z.set_xlim(view[0],view[2]);z.set_ylim(view[1],view[3]);z.set_aspect('equal');z.set_title('Actual centre entry, FFs and native M5/M6 PG\nNo M5/M6 PG rectangle overlaps ck; empty4.32um bay');z.set_xlabel('um');z.set_ylabel('um');fig.suptitle('DISABLED hist zero-cycle internal repack + coherent centre M5 entry — NATIVE new FP/TAP/PG + FF anchors\nPG64 terms/2700 shapes touched; pins1803/1803 PASS. No PLACE/CTS/route/TTFF or source-qualification claim.',fontsize=12);fig.tight_layout();fig.savefig(P/'actual_fp_anchored_LOOK.png',dpi=170)
print('actual FF statuses',collections.Counter(r['status']for r in F),'dont_touch',sum(r['dont_touch']for r in F))
