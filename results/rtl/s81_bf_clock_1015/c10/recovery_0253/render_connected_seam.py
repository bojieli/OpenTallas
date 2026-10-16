import re,json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parents[5];out=root/'results/rtl/s81_bf_clock_1015/c10/recovery_0253';import subprocess
text=subprocess.check_output(['git','show','origin/main:physical/s81_die_views/bf_compact199/ot_v41_bf_col/ot_v41_bf_col.lef'],cwd=root,text=True);pins={}
for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n',text,re.S):
 a=re.search(r'LAYER (\S+) ;\s+RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2]);
 if a:pins[m[1]]=(a[1],(float(a[3])+float(a[5]))/2)
f=json.load(open(root/'physical/ref_tile_specs/s81_bf_native_1015/static_pins_c10s/pin_request.json'))['pins'];pairs=[]
for nm,p in f.items():
 if not nm.startswith('c0['):continue
 src=p['source_pin'][3:]
 if src in pins:pairs.append((nm,src,pins[src][1],p['y']))
assert len(pairs)==776,len(pairs)
rec={'scope':'Connected producer geometry diagnostic; column is published compact199 view, front c10 requested pins. No die re-pin/fanout grant claimed.','front_pin_request':'physical/ref_tile_specs/s81_bf_native_1015/static_pins_c10s/pin_request.json','column_lef':'physical/s81_die_views/bf_compact199/ot_v41_bf_col/ot_v41_bf_col.lef','column_lef_sha256':hashlib.sha256(text.encode()).hexdigest(),'matched_seam_bits_one_face':len(pairs),'unaligned_y':sum(abs(a-b)>1e-6 for _,_,a,b in pairs),'max_vertical_jog_um':max(abs(a-b) for _,_,a,b in pairs),'old_column_y_range':[min(a for _,_,a,b in pairs),max(a for _,_,a,b in pairs)],'c10_front_y_range':[min(b for _,_,a,b in pairs),max(b for _,_,a,b in pairs)],'required_fix':'Die must adopt source-bound column re-pin matching the c10 stretch or allocate and route an explicit fanout channel; 1.188um historical straight seam is not proven.'};(out/'connected_seam_audit.json').write_text(json.dumps(rec,indent=2)+'\n')
fig,axes=plt.subplots(1,2,figsize=(14,7),gridspec_kw={'width_ratios':[1.3,1]})
a=axes[0];cw=450.144;fw=116.64;gap=1.188
for x,w,label in [(0,cw,'closed column R0'),(cw+gap,fw,'c10 front'),(cw+2*gap+fw,cw,'closed column MY')]:a.add_patch(Rectangle((x,0),w,198.72,fill=False));a.text(x+w/2,100,label,ha='center')
a.set(xlim=(-5,1025),ylim=(-5,205),xlabel='um',ylabel='um',title='Actual requested outlines; whole three-block assembly');a.set_aspect('equal')
a=axes[1]
for _,_,cy,fy in pairs[::12]:a.plot([0,1],[cy,fy],color='tab:blue',alpha=.35,lw=.6)
a.scatter([0]*len(pairs),[c for _,_,c,f in pairs],s=1,color='orange',label='closed column E')
a.scatter([1]*len(pairs),[f for _,_,c,f in pairs],s=1,color='purple',label='c10 front W')
a.set(xticks=[0,1],xticklabels=['column E','front W'],ylabel='actual y (um)',ylim=(0,199),title='Seam pin context (x expanded for readability)');a.legend(loc='lower center');fig.suptitle(f'BF connected-pin diagnostic: 776/776 y mismatches; max jog {rec["max_vertical_jog_um"]:.1f} um\nFix: column re-pin or explicit routed fanout channel required')
fig.tight_layout();fig.savefig(out/'connected_seam.png',dpi=150);print(rec)
