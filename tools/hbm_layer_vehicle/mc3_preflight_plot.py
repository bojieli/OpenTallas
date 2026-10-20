#!/usr/bin/env python3
"""Render actual native preflight geometry; never implies placed qualification."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def main():
 ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('output');a=ap.parse_args()
 g=json.loads(Path(a.geometry).read_text());fig,(ax,z)=plt.subplots(1,2,figsize=(15,8),gridspec_kw={'width_ratios':[1.15,1]})
 colors=dict(BULK='#bdd4ee',HEADER='#f5cc8b',RESET='#f4aaaa',NFACE='#e1c281',SCAP='#dfc4b4',WCAP='#aaaada',ECAP='#aaaada')
 for panel in (ax,z):
  panel.add_patch(Rectangle((0,0),388.8,388.8,facecolor='#f9fafb',edgecolor='black'))
  for name,r in g['groups'].items():
   color=colors.get(name.removeprefix('mc3_'),'#b7dec9')
   for x0,y0,x1,y1 in r['rects']:panel.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=color,edgecolor=color,alpha=.5))
  for m in g['macros']:
   x0,y0,x1,y1=m['bbox'];panel.add_patch(Rectangle((x0-5.4,y0-5.4),x1-x0+10.8,y1-y0+10.8,fill=False,edgecolor='#aaa',linestyle=':',linewidth=.6))
   panel.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#cbb7dc',edgecolor='#555',linewidth=.7))
  for i in g['firm']:
   x0,y0,x1,y1=i['bbox'];panel.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#255c43',linewidth=0))
  panel.grid(alpha=.15);panel.set_aspect('equal');panel.set_xlabel('µm');panel.set_ylabel('µm')
 ax.set_xlim(-5,393.8);ax.set_ylim(-5,393.8)
 ax.text(190,209,'Connected bulk fence\n40.21% measured cell area\ncentral reset island excluded',ha='center',va='center',fontsize=8)
 ax.text(190,291,'Native HEADER fence\nmatched I/O control cones',ha='center',fontsize=8)
 ax.plot([0],[208.14],marker='>',color='red',markersize=8);ax.text(5,218,'clk / reset',color='red',fontsize=7)
 z.set_xlim(110,208);z.set_ylim(373,389.8);z.set_title('Actual packed N1 / control hold cells\n0.054 µm horizontal spacing; native master widths',fontsize=10)
 ax.set_title('Native macro / fence / FIRM preflight\n23 literal 43.2 µm macro origins; 5.4 µm PG halos',fontsize=10)
 fig.suptitle('MC3c v6 bounded preflight — unplaced bulk; no GPL / CTS / route\nNative ODB SHA256 '+g['odb_sha256'][:20],fontsize=12)
 fig.text(.52,.1,'FIRM cells are actual native rectangles. Colored regions are constraints,\nnot placed standard-cell occupancy. PG conductor / clock / setup-hold\nqualification and parent relay / phase integration remain OPEN.',ha='left',fontsize=10)
 fig.tight_layout(rect=(0,0,1,.93));fig.savefig(a.output,dpi=160);plt.close(fig)

if __name__=='__main__':main()
