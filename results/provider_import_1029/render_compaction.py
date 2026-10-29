import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
old=json.load(open(sys.argv[1]));new=json.load(open(sys.argv[2]));inv=json.load(open(sys.argv[3]));ctx=json.load(open(sys.argv[4]));D=new['dbu'];role={c['inst']:c.get('role','origin') for c in inv['cells']};fig,ax=plt.subplots(2,2,figsize=(14,8));stages=['r1035_1','b1036']
for col,stage in enumerate(stages):
 allc=[c for pl in [old,new] for c in pl['cells'] if c['stage']==stage];xmin=min(c['bbox_dbu'][0] for c in allc)/D-1;xmax=max(c['bbox_dbu'][2] for c in allc)/D+2;ymin=min(c['bbox_dbu'][1] for c in allc)/D-.6;ymax=max(c['bbox_dbu'][3] for c in allc)/D+.6
 for row,pl in enumerate([old,new]):
  aa=ax[row,col]
  for n,m,x,y,X,Y in ctx['existing_cells']:
   x,y,X,Y=[v/D for v in [x,y,X,Y]]
   if x<xmax and xmin<X and y<ymax and ymin<Y:aa.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#7d878f',alpha=.8))
  for c in pl['cells']:
   if c['stage']!=stage:continue
   x,y,X,Y=[v/D for v in c['bbox_dbu']];colour=('#8056ac' if role[c['inst']]=='reset' else '#1768b4') if c['sequential'] else '#d59025';aa.add_patch(Rectangle((x,y),X-x,Y-y,facecolor=colour,edgecolor='white',linewidth=.5))
  aa.set(xlim=(xmin,xmax),ylim=(ymin,ymax),title=('Original' if row==0 else '3-column FF compact')+' '+stage,xlabel='um',ylabel='um');aa.set_aspect('equal')
fig.suptitle('Whole-FF bound407.43→404.784um; exact registered max401.67um. OriginFFblue/resetFFpurple/comb orange/frozenclock grey.');fig.tight_layout();fig.savefig(sys.argv[5],dpi=150)
