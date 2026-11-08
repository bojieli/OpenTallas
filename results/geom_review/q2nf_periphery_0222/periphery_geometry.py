import json,pathlib,collections,copy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=pathlib.Path(__file__).resolve().parent
d=copy.deepcopy(json.loads((root/'geometry.json').read_text()));old=d['outline'];d['outline']=[708.48,311.04];W,H=d['outline']
for i,m in enumerate(d['macros']):
 if i<8:
  m['x']=34.56 if i<4 else 617.76;m['y']=77.76+(i%4)*43.2
 elif i<14:
  m['x']=34.56+((i-8)//2)*234.168;m['y']=34.56 if i%2==0 else 248.4
 elif i<18:
  m['x']=190.08 if i%2==0 else 450.144;m['y']=110.592 if i<16 else 188.352
 else:m['x']=321.84;m['y']=77.76
for f in ['N','S','E','W']:
 a=sorted((p for p in d['pins']if p.get('face')==f),key=lambda p:(p['x']if f in'NS'else p['y'],p['bus'],p['bit']))
 span=W if f in'NS'else H;count=len(a);lo=8.64;hi=span-8.64
 for j,p in enumerate(a):
  v=.024+round((lo+(j+.5)*(hi-lo)/count-.024)/.048)*.048
  p['x'],p['y']=(v,H if f=='N'else 0)if f in'NS'else(W if f=='E'else 0,v)
clocks=[p for p in d['pins']if p.get('face')=='I']
clock_sites=collections.Counter()
for p in clocks:
 b=p['bus'];k=p['bit']
 if b=='clk_issue':x,y=354.24,155.52
 elif b=='clk_control':x,y=354.24,129.6
 elif b=='clk_program':x,y=354.24,120.96
 elif b=='clk_reduce':x,y=354.24,216.0
 elif b=='clk_link':x,y=(125.28 if k<5 else 580.608),155.52
 elif b=='clk_qslots':x,y=[125.28,285.12,354.24,423.36,580.608][k%5],146.88 if k<5 else 233.28
 elif b=='clk_upipe':x,y=[125.28,285.12,423.36,580.608][k%4],[100.224,146.88,190.08,233.28][k//4]
 else:raise ValueError(b)
 # Independent ports share physical station only if distinct BPin tracks.
 p['x']=.024+round((x+clock_sites[x,y]*.192-.024)/.048)*.048;p['y']=y;clock_sites[x,y]+=1
seen=set()
for p in d['pins']:
 q=(p['layer'],round(p['x'],3),round(p['y'],3));assert q not in seen,q;seen.add(q)
for i,m in enumerate(d['macros']):
 assert m['x']>=4.32 and m['y']>=4.32 and m['x']+m['w']<=W-4.32 and m['y']+m['h']<=H-4.32
 for n in d['macros'][i+1:]:
  assert m['x']+m['w']+8.64<=n['x']or n['x']+n['w']+8.64<=m['x']or m['y']+m['h']+8.64<=n['y']or n['y']+n['h']+8.64<=m['y'],(i,n)
for p in clocks:
 assert all(not(m['x']-4.32<=p['x']<=m['x']+m['w']+4.32 and m['y']-4.32<=p['y']<=m['y']+m['h']+4.32)for m in d['macros']),p
(root/'periphery_geometry.json').write_text(json.dumps(d,indent=1))
fig,ax=plt.subplots(figsize=(12,10));ax.add_patch(Rectangle((0,0),W,H,fill=False))
for i,m in enumerate(d['macros']):
 x,y=m['x'],m['y'];w,h=m['w'],m['h'];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,color='orange',alpha=.18));ax.add_patch(Rectangle((x,y),w,h,color='grey',alpha=.7));ax.text(x+w/2,y+h/2,str(i),ha='center',va='center',fontsize=8)
for L,c in [('M4','royalblue'),('M5','seagreen')]:
 a=[v for v in d['pins']if v['layer']==L];ax.scatter([v['x']for v in a],[v['y']for v in a],s=2,c=c,label=L)
for p in clocks:ax.scatter([p['x']],[p['y']],s=60,c='red',marker='*')
ax.set_aspect('equal');ax.set_xlim(-8,W+8);ax.set_ylim(-8,H+8);ax.set_title('Q2NF periphery candidate ONLY: 708.48 x311.04um\n19 macros, 6222 pins, clock entries in channels; no POR adoption');ax.legend();fig.tight_layout();fig.savefig(root/'q2nf_periphery_candidate.png',dpi=140)
print('GEOMETRY',len(d['macros']),'macro halos clear;',len(d['pins']),'unique legal-grid pin sites; clocks off halos')
