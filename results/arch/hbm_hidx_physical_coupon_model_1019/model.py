import json,csv,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent
D=140.4;lo=2.16;hi=D-lo;pitch=.192
outputs=[f'compacted[{i}]' for i in range(288)]+[f'pair_select[{i}]' for i in range(576)]+[f'quad_select[{i}]' for i in range(1440)]
inputs=[f'lane_v[{i}]' for i in range(16)]+[f'payload[{i}]' for i in range(288)]
west=inputs+outputs[:348];west.insert(326,'clk')
ports={'W':west,'N':outputs[348:1000],'E':outputs[1000:1652],'S':outputs[1652:]}
rows=[]
for face,names in ports.items():
 start=(D-(len(names)-1)*pitch)/2
 for i,name in enumerate(names):
  t=start+i*pitch;x,y={'W':(0,t),'E':(D,t),'S':(t,0),'N':(t,D)}[face]
  rows.append(dict(port=name,face=face,x_um=round(x,6),y_um=round(y,6),role='clock' if name=='clk' else 'input_data' if name in inputs else 'registered_output'))
 assert start>=lo and start+(len(names)-1)*pitch<=hi
with (p/'ports.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
# Density counts inclusive 1um windows.
density={}
for face,names in ports.items():
 vals=sorted(r['y_um'] if face in 'WE' else r['x_um'] for r in rows if r['face']==face)
 density[face]=max(sum(x<=y<=x+1+1e-9 for y in vals) for x in vals)
 assert density[face]<=6
m=dict(scope='MODEL only; no placement/CTS/route',die_um=[D,D],core_um=[lo,lo,hi,hi],site_um=[.054,.27],rows=round((hi-lo)/.27),pin_pitch_um=pitch,face_counts={k:len(v) for k,v in ports.items()},max_pins_any_1um=density,max_manhattan_um=2*D,existing_cells=8265,existing_ff=2616,new_capture_ff=288,new_polarity_inverters=288,candidate_cells_before_cts=11145,candidate_ff=2904,candidate_area_um2=1651.18308,candidate_clock_cap_ff=1378.633344,core_util=1651.18308/(hi-lo)**2,reset_endpoints=0,clock_sinks=2904,pg_native_terminals_before_cts=11145*2,unknown_cts_area=None,unknown_parent_fit=None)
(p/'model.json').write_text(json.dumps(m,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(11,10));ax.set_aspect('equal')
ax.add_patch(Rectangle((0,0),D,D,fill=False,lw=2));ax.add_patch(Rectangle((lo,lo),hi-lo,hi-lo,facecolor='#fafafa',edgecolor='gray'))
# Actual row lattice, then conceptual cell-allocation bands, never claimed placement.
for i in range(m['rows']):
 y=lo+i*.27
 ax.plot([lo,hi],[y,y],color='#dddddd',lw=.12)
# Ring of 55% local-util cell bands: area exact from ordinary-cell inventory.
needed=m['candidate_area_um2']/.55;side=hi-lo;t=(side-math.sqrt(side*side-needed))/2
bands=[(lo,lo,side,t),(lo,hi-t,side,t),(lo,lo+t,t,side-2*t),(hi-t,lo+t,t,side-2*t)]
for x,y,w,h in bands:ax.add_patch(Rectangle((x,y),w,h,facecolor='#b4d9ed',edgecolor='#407c9e',alpha=.85))
for role,c in [('input_data','#ce6a32'),('registered_output','#1b7f65'),('clock','#b92297')]:
 a=[r for r in rows if r['role']==role];ax.scatter([r['x_um'] for r in a],[r['y_um'] for r in a],s=3 if role!='clock' else 45,c=c,label=role,zorder=5)
clock=next(r for r in rows if r['role']=='clock');ax.annotate('Clock entry; real CTS OPEN',(clock['x_um'],clock['y_um']),xytext=(20,73),arrowprops=dict(arrowstyle='->'),fontsize=10)
ax.text(D/2,113,'MODEL ONLY — no cells placed',ha='center',fontsize=14,weight='bold')
ax.text(D/2,93,'2904 actual FF clock sinks; 11145 pre-CTS cells\nRegistered outputs: 2304; input data: 304\n288 S1 captures + 288 INV + 2304 BUF8 added\nAll 504 legal rows retained',ha='center',fontsize=12)
ax.text(D/2,49,f'Cell allocation bands: {t:.3f} um at 55% local fill\nNative ordinary area 1651.18308 um²\nWhole-core fill 8.917%: PIN-BOUND, ROOT HOLD\nNo utilization exception assumed',ha='center',fontsize=11)
ax.text(D/2,25,'Every point-to-point Manhattan path ≤280.8 um\nEach full face .192 um pitch; max6 pins /1um\nNative PG rails/vias/coverage remain OPEN',ha='center',fontsize=11)
for face,n in m['face_counts'].items():
 xy={'N':(D/2,D+3),'S':(D/2,-6),'W':(-9,D/2),'E':(D+9,D/2)}[face];ax.text(*xy,f'{face}: {n}',ha='center',rotation=90 if face in 'WE' else 0)
ax.set_xlim(-15,D+15);ax.set_ylim(-12,D+10);ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='upper right',fontsize=8)
fig.tight_layout();fig.savefig(p/'MODEL.png',dpi=180)
print(json.dumps(m,indent=2))
