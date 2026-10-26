#!/usr/bin/env python3
"""Render candidate homes of actual mapped FF and soft clock drops; never label this an ODB/route result."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--type',required=True);p.add_argument('--sites',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);q=p.parse_args();t=json.loads(q.plan.read_text())['partition_types'][q.type];sites=json.loads(q.sites.read_text());summary=json.loads(q.summary.read_text());fig,ax=plt.subplots(figsize=(10,15));colors={'delay':'#2563eb','fabric':'#f59e0b','boundary':'#16a34a','other':'#e11d48','reset_start':'#6b7280'}
 for c in t.get('hard_cores',[]):
  x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#e5e7eb',edgecolor='black'));ax.text(x+w/2,y+h/2,c['inst']+'\n'+c.get('orient','R0'),ha='center')
 for cat,color in colors.items():
  rows=[s for s in sites if s['category']==cat]
  if rows:ax.scatter([s['x_um'] for s in rows],[s['y_um'] for s in rows],s=.5,c=color,label=f'{cat}: {len(rows):,} FF',rasterized=True)
 ck=summary['clock_ports'];ax.scatter([c['x'] for c in ck],[c['y'] for c in ck],s=20,c='#7e22ce',marker='x',label=f'{len(ck)} candidate soft clock drops')
 ax.set(xlim=(0,t['outline_um'][0]),ylim=(0,t['outline_um'][1]),aspect='equal',xlabel='um',ylabel='um',title=f"{q.type}: {len(sites):,} actual final6 mapped FF, candidate sites\n{len(ck)} soft drops; max {summary['max_clock_sinks']} sinks / {summary['max_clock_radius_um']:.1f} um radius\nNot DPL / route: native hard views+provider CTS missing; final7 D4 update pending")
 ax.legend(loc='upper left',fontsize=8);fig.tight_layout();fig.savefig(q.out,dpi=140)
if __name__=='__main__':main()
