#!/usr/bin/env python3
"""Render dump_render.py output: overview (left) + zoom window (right)."""
import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
d=json.load(open(sys.argv[1]));title=sys.argv[3];U=1000.
def rects(rs,**kw):return PatchCollection([Rectangle((r[0]/U,r[1]/U),(r[2]-r[0])/U,(r[3]-r[1])/U) for r in rs],**kw)
fig,(a0,a1)=plt.subplots(1,2,figsize=(18,11),gridspec_kw=dict(width_ratios=[1,1.6]))
a0.add_collection(rects([p[1:] for p in d['parts']],facecolor='none',edgecolor='k',lw=.3))
a0.add_collection(rects(d['hard'],facecolor='red',edgecolor='none',alpha=.6))
xs=[c[0]/U for c in d['allclock']];ys=[c[1]/U for c in d['allclock']];a0.scatter(xs,ys,s=.2,c='green')
w=d['win'];a0.add_patch(Rectangle((w[0],w[1]),w[2]-w[0],w[3]-w[1],fill=False,edgecolor='blue',lw=1.5))
a0.set_xlim(0,d['die'][2]/U);a0.set_ylim(0,d['die'][3]/U);a0.set_aspect('equal');a0.set_title('die: partitions, hard cores (red), %d clock bodies (green), zoom (blue)'%len(d['allclock']),fontsize=9)
a1.add_collection(rects(d['obs'],facecolor='0.75',edgecolor='0.55',lw=.2))
a1.add_collection(rects(d['hard'],facecolor='red',edgecolor='none',alpha=.6))
a1.add_collection(rects(d['provider'],facecolor='orange',edgecolor='k',lw=.15))
a1.add_collection(rects(d['clock'],facecolor='green',edgecolor='k',lw=.15))
a1.add_collection(rects([p[1:] for p in d['parts']],facecolor='none',edgecolor='k',lw=.8))
a1.set_xlim(w[0],w[2]);a1.set_ylim(w[1],w[3]);a1.set_aspect('equal')
a1.set_title('zoom: M1 master OBS (grey), clock (green %d), provider (orange %d), hard (red)'%(len(d['clock']),len(d['provider'])),fontsize=9)
fig.suptitle(title,fontsize=11);fig.tight_layout();fig.savefig(sys.argv[2],dpi=110)
