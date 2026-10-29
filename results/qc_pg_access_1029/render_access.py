#!/usr/bin/env python3
import json,argparse
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args();g=json.load(open(Path(a.input)/'geometry.json'));plan=json.load(open(a.plan));qs=plan['paths'];q=qs[0];r=q['rail'];x0,y0,x1,y1=[v/1000 for v in r];bounds=(x0-1,y0-1.2,x1+1,y1+1.2)
fig,axes=plt.subplots(1,2,figsize=(15,6));fig.suptitle('QC actual26 power-access construction: scoped first100 contacts, no timing / IR claim')
colors={'M1':'#777777','M2':'#A086B7','M3':'#6887BC','M4':'#91B188','M5':'#D8AE7B','M6':'#B38AC2','M7':'#ee7c22','M8':'#159ca3','M9':'#bb277a'}
def draw(ax,ly,r,**kw):
 xx,yy,xx1,yy1=[v/1000 for v in r]
 if xx1<bounds[0] or xx>bounds[2] or yy1<bounds[1] or yy>bounds[3]:return
 ax.add_patch(Rectangle((xx,yy),xx1-xx,yy1-yy,color=colors[ly],**kw))
for ax in axes:
 ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_aspect('equal');ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.grid(alpha=.2)
for _,_,ly,*rr in g['signal_shapes']:
 if ly=='M1':draw(axes[0],ly,rr,alpha=.7)
for qq in qs:
 n=qq['net'];rr=qq['rail'];draw(axes[0],'M1',rr,alpha=.7)
 x,y=qq['stack'];draw(axes[0],'M1',[x-9,y-11,x+9,y+11],alpha=1)
 if bounds[0]<=x/1000<=bounds[2] and bounds[1]<=y/1000<=bounds[3]:axes[0].text(x/1000,y/1000,n,fontsize=7,color='red' if n=='VDD' else 'blue')
 for ly,rx,ry in [('M2',25,9),('M3',9,25),('M4',48,12),('M5',12,48),('M6',40,16)]:draw(axes[1],ly,[x-rx,y-ry,x+rx,y+ry],alpha=.8)
 xx,yy,ex,ey=qq['m8'];draw(axes[1],'M7',[x-16,min(y,yy)-40,x+16,max(y,yy)+40],alpha=.8);draw(axes[1],'M8',[min(xx,ex)-40,yy-20,max(xx,ex)+40,yy+20],alpha=.8)
axes[0].set_title('Native M1 A/Y and supply rails; outward VIA12 landings');axes[1].set_title('Minarea tower pads, M7 stems, M8 bridges to real M9')
fig.tight_layout();fig.savefig(a.out,dpi=180)
