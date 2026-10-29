#!/usr/bin/env python3
"""Render a newly planned parent trunk before its insertion into the placed kit."""
import json,sys,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1]));g=json.load(open(sys.argv[3] if len(sys.argv)>3 else p['cl']));f,a=plt.subplots(figsize=(7,13));a.add_patch(Rectangle((0,0),g['W'],g['H'],fill=False))
for x0,y0,x1,y1 in g['macros']:a.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#b7c7db',edgecolor='#8b9aa8',alpha=.65))
by={i['name']:i for i in p['insts']};pts={i['out_net']:tuple(i['p']) for i in p['insts']}
for i in p['insts']:
 x,y=i['p'];up=pts.get(i['in_net'])
 if up:a.plot([up[0],x],[up[1],y],color='#c9693f',lw=.65,alpha=.65)
 a.plot(x,y,'.',color='#9a4427',ms=2)
for c in g['clusters']:
 x,y=c['root'];a.plot(x,y,'o',mfc='#2c855f' if c.get('ungated') else '#46769a',ms=3)
e=p['summary']['entry'];a.plot(*e,'r*',ms=14);a.set(xlim=(-5,g['W']+5),ylim=(-5,g['H']+5));a.set_aspect('equal');a.set_title('Planned A0 parent trunk: red clock entry, green ungated clusters');f.savefig(sys.argv[2],dpi=150,bbox_inches='tight')
