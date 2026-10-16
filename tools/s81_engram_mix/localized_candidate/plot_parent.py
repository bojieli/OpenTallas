#!/usr/bin/env python3
"""To-scale source-connected parent candidate and actual failing child pinlegs."""
import argparse,json,re,subprocess,itertools,hashlib
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--joint',type=Path,required=True);a=p.parse_args();O=a.out;R=Path(__file__).resolve().parents[3];g=json.loads((O/'connected_geometry.json').read_text());t=json.loads((O/'perbit_timing.json').read_text());boxes=g['results']['Q_cooptimized_capsules']['placement'];joint=json.loads(a.joint.read_text());W,H=joint['outline_um'];pins={}
for m,v in g['leaf_views'].items():
 s=subprocess.check_output(['git','show',v['record']+':'+v['path']],cwd=R).decode();pins[m]={}
 for pm in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):
  pins[m][pm[1]]=[((float(x)+float(z))/2,(float(y)+float(w))/2)for x,y,z,w in re.findall(r'RECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',pm[2])]
def points(row,side):
 n,pin=row[side];b=boxes[n];return[(b['x']+x,b['y']+y)for x,y in pins[row[side+'_master']][pin]]
seen=set();critical=[]
for row in t['worst_setup150']:
 if row['selected_setup_ps']>=0:continue
 key=tuple((row[k][0],row[k][1].split('[')[0])for k in ['source','target'])
 if key in seen:continue
 seen.add(key);critical.append(row)
 if len(critical)==10:break
fig,(ax,bx)=plt.subplots(1,2,figsize=(16,15),gridspec_kw={'width_ratios':[1,2]});bottoms=[30.24,943.92,1857.60,2771.28]
for q,oy in enumerate(bottoms):
 for n,b in boxes.items():ax.add_patch(Rectangle((b['x'],b['y']+oy),b['w'],b['h'],facecolor='#b2df8a'if n.startswith('shell.')else'#c4d2e8',edgecolor='black',lw=.2))
 ax.text(20,oy+851.04,f'copy{q}: R0 38children',fontsize=8,va='bottom')
 for v in [74.748+913.152*q,838.428+913.152*q]:ax.plot([W,W+21.624],[v,v],color='red',lw=1)
 ax.plot([W,W],[74.748+913.152*q,838.428+913.152*q],color='red',lw=3)
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5));ax.axvline(1028.16,color='orange',ls='--');ax.axvline(W+21.624,color='purple');ax.text(1100,1800,'E transport reserve\n403.464um postshave\n403.488um nominal\n\nRoot0 control,\n40 RS5 stations,\n20return+4request\ncaptures UNPLACED\n\nH/V broadcast and\nwrite transpose OPEN',ha='center',fontsize=8);ax.set_xlim(-20,W+80);ax.set_ylim(-20,H+40);ax.set_aspect('equal');ax.set_title('SLOT A: q0 SOUTH; actual joint candidate E/W bands\n1431.624x3652.536um, VM seam21.624um',fontsize=10)
for n,b in boxes.items():
 bx.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#b2df8a'if n.startswith('shell.')else'#c4d2e8',edgecolor='black',lw=.5));bx.text(b['x']+b['w']/2,b['y']+b['h']/2,n.replace('mix.','').replace('shell.','s.').replace('.leaf',''),ha='center',va='center',fontsize=6)
colors=plt.cm.tab10.colors
for i,row in enumerate(critical):
 (x,y),(u,v)=min(itertools.product(points(row,'source'),points(row,'target')),key=lambda pair:abs(pair[0][0]-pair[1][0])+abs(pair[0][1]-pair[1][1]));bx.plot([x,u,u],[y,y,v],ls='--',color=colors[i],lw=1.2);bx.plot([x,u],[y,v],'.',color=colors[i]);bx.text((x+u)/2,(y+v)/2,str(i+1),color=colors[i],fontsize=9,fontweight='bold')
r=g['results']['Q_cooptimized_capsules']
for axis in ['x','y']:
 cut=r['mandatory_cut_inventory'][axis][0];value=cut['position_um'];(bx.axvline if axis=='x'else bx.axhline)(value,color='black',ls=':',lw=1.5)
bx.set_xlim(-10,1050);bx.set_ylim(-10,880);bx.set_aspect('equal');bx.set_title(f'Actual-TT R0 search: {t["selected_actual_R_rule_fail_bits"]} negativebits; worst {t["selected_min_setup_ps"]:.2f}ps\nTop10 grouped failing actual pinlegs; dotted critical cuts',fontsize=11)
legend='\n'.join(f'{i+1}: '+r['source'][0]+'.'+r['source'][1]+' -> '+r['target'][0]+'.'+r['target'][1]+f'  {r["selected_setup_ps"]:.1f}ps / {r["distance_um"]:.1f}um'for i,r in enumerate(critical));fig.text(.41,.06,legend,fontsize=7,va='bottom');fig.suptitle('Necessary optimistic geometry only: dashed L1 legs may cross hard outlines; not routed paths\nNo fullparent timing, clock/reset, PG, station, pin-access or native qualification; no inherited54um N strip',fontsize=12);fig.subplots_adjust(bottom=.22,top=.93);fig.savefig(O/'parent_actual_timing.png',dpi=170)
(O/'parent_figure_receipt.json').write_text(json.dumps({'joint_sha256':hashlib.sha256(a.joint.read_bytes()).hexdigest(),'joint_source':'die candidate d0323e2d2; not adopted','copy_bottoms_um':bottoms,'parent_outline_um':[W,H],'actual_E_channel_um':W-1028.16,'nominal_E_channel_um':403.488,'top_grouped_actual_failing_legs':critical,'placement_scope':'R0 candidate exact38hard outlines/copy; remaining65roots have no placed physicalview; all parent source transpose/broadcast transports remain OPEN'},indent=1)+'\n')
