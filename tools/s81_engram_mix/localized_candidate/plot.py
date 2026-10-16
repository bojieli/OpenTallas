#!/usr/bin/env python3
"""To-scale granted SLOT A and measured leaf outlines; channels are reservations."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 screen=json.loads((R/'results/arch/s81_hc_2330/mix4_current_geometry/screen.json').read_text())
 W,H=1431.648,3652.56;C=876.96
 fig,(ax,notes)=plt.subplots(1,2,figsize=(12,13),gridspec_kw={'width_ratios':[1.15,1]})
 ax.add_patch(Rectangle((0,0),W,H,fill=False,linewidth=2));ax.add_patch(Rectangle((C+2.16,2.16),550.368,H-4.32,facecolor='#daeaf5',alpha=.5,hatch='..',edgecolor='#6699bb'))
 ax.add_patch(Rectangle((2.16,H-56.16),C,54,facecolor='#ffdca3',edgecolor='black'))
 ax.text(C/2,H-29,'ck0 control/descriptor: unlocalized',ha='center',va='center',fontsize=8)
 for copy in range(4):
  yn=77.76+copy*(C+21.6);y=H-yn-C
  ax.add_patch(Rectangle((2.16,y),C,C,fill=False,linewidth=1.5))
  for b in screen['cluster']['boxes']:
   col='#b2df8a' if b['master'] in ('mixq_shcol','mixq_shctl') else '#b6c5e0'
   ax.add_patch(Rectangle((2.16+b['x'],H-yn-b['y']-b['h']),b['w'],b['h'],facecolor=col,edgecolor='#555555',linewidth=.4))
  ax.text(20,y+C/2,f'copy{copy}\n38 actual leaf outlines',ha='left',va='center',fontsize=9,bbox={'facecolor':'white','alpha':.85,'edgecolor':'none'})
  ax.text(C+277,y+C/2,f'5 ingress roots\nclock {193+5*copy}..{197+5*copy}\nrequest root{213+copy}\nRS5 station transport\nlocation/pins OPEN',ha='center',va='center',fontsize=8)
 # Full-height VM interface; exact per-bit y locations have not been granted.
 ax.axvline(W+21.6,color='#cc3333',linewidth=3)
 ax.text(W+60,H/2,'VM W face at die x11898.144\n21.6um seam; per-bit lane bands OPEN',rotation=90,ha='center',va='center',fontsize=9)
 ax.annotate('S/W command face to SSEQ',xy=(300,0),xytext=(300,-180),ha='center',arrowprops={'arrowstyle':'->'},fontsize=9)
 ax.set_xlim(-35,W+160);ax.set_ylim(-250,H+75);ax.set_aspect('equal');ax.set_xlabel('local x (um)');ax.set_ylabel('local y (um)')
 ax.set_title('SLOT A:1431.648 x3652.56um\ndie origin(10444.896,16802.64)',fontsize=11)
 notes.axis('off');text='''IMPLEMENTED CAPTURE CANDIDATE:217 CLOCK ROOTS

193 unchanged baseline roots:
  1 top control +152 cluster +40 RS5 stations
24 actual new independent entries:
  20 return captures x513 FF
  4 request captures x75 FF
10,560 existing FF moved off ck0
0 added FF;0 added capture edges

PROOF SCOPE
Capture sequential equivalence:1024 vectors,
17 resets;10,813,440 bit comparisons.
Stopped ingress/request clock mutants rejected.
Original193-root all-FP-RTL810cycle proof
remains tied to b4ca1edc9; no new full numerical
or native217-root qualification claimed.

ACTUAL CONNECTED PATHS STILL OPEN
H:each of4 VM H lanes sends128bits to each
of4 copies (128 groups x16bits).
V:VM lanes1/2 broadcast1024bits to all4copies.
K/W:own-copy lanes through grouped stations.
Requests:4 x75bits plus copy0 descriptor override.
Descriptor/start/control and shared tags still ck0.
Reset, grouped stations, full logical-clock delivery,
per-bit placement/reach/cuts/PG and native route
are all OPEN. Keep RS5 pending physical proof.

DRAWING SCOPE
152 child rectangles use the11 actual routed
leaf sizes. Blue area is a reserved transport
channel, not placed capture/station hard macros.
Orange54um strip is a planning reservation.
Locations of new roots are labels only.
No native parent/VM/layer/token closure claimed.'''
 notes.text(0,1,text,ha='left',va='top',fontsize=10,linespacing=1.35)
 fig.suptitle('MIX4 current connected plan:source-backed capture partition; physical incident proof OPEN',fontsize=13)
 fig.savefig(a.out/'slot_A_217_connected.png',dpi=150,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':main()
