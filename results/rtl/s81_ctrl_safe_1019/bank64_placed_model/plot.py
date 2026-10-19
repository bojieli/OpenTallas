from pathlib import Path
import csv, collections, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
p=Path('/home/ubuntu/wt/codex-s81-ctrl-bank64/results/rtl/s81_ctrl_safe_1019/bank64_placed_model')
r=list(csv.DictReader((p/'instances.tsv').open(),delimiter='\t'))
for x in r:
    for k in ('x','y','w','h','area'): x[k]=float(x[k])
    x['class']='macro' if x['block']=='1' else 'physical' if x['name'].startswith(('TAP_','PHY_')) else 'input hold' if x['name'].startswith(('ot_inhold','ot_ih')) else 'output hold' if x['name'].startswith(('ot_outhold','ot_oh')) else 'cloned face helpers' if x['name'].startswith('ot_prs') else 'other std'
cnt=collections.Counter(x['class'] for x in r)
areas={k:sum(x['area'] for x in r if x['class']==k) for k in cnt}
std=sum(x['area'] for x in r if x['block']=='0')
mac=sum(x['area'] for x in r if x['block']=='1')
band=[x for x in r if x['block']=='0' and 129.6<=x['y']+x['h']/2<133.92]
s={'status':'PLACEMENT_ONLY_DIAGNOSTIC_NO_CTS_OR_ADOPTION','outline_um':[531.25,250],'macros':22,'instances':len(r),'std_area_um2':std,'macro_area_um2':mac,'areas_by_name_class_um2':areas,'counts_by_name_class':dict(cnt),'old_proposed_central_band_um':[2.16,129.6,529.09,133.92],'actual_cells_centered_in_old_central_band':len(band),'actual_area_centered_in_old_central_band_um2':sum(x['area'] for x in band),'old_proposed_band_fill_actual':sum(x['area'] for x in band)/((529.09-2.16)*(133.92-129.6)),'functional_std_area_um2':std-areas['physical'],'central_band_functional_area_um2':sum(x['area'] for x in band if x['class']!='physical'),'flow_exit':0,'placement_violations':0,'source_fifo':'de58d09a7','source_macro':'e26d92503','blockers':['No constrained standard-cell band; full-row diagnostic does not qualify fill','Source reset fanout and original protected-net CTS clone failure remain independent','CDC sampled-age/phase/collision and actual root-native TT/FF not qualified','PG contact/escape and actual parent fit/electrical not qualified','Old central-band arithmetic estimate cannot substitute measured placed mass']}
(p/'measured.json').write_text(json.dumps(s,indent=2)+'\n')
colors={'macro':'#23395d','physical':'#d5dbe2','input hold':'#f39c12','output hold':'#cf5c36','cloned face helpers':'#9c5cad','other std':'#2a9d8f'}
f,a=plt.subplots(figsize=(14,7))
a.add_patch(Rectangle((0,0),531.25,250,fill=False,color='black',lw=1.5))
for k in colors:
    cells=[x for x in r if x['class']==k and x['area']>0]
    pa=[Rectangle((x['x'],x['y']),x['w'],x['h']) for x in cells]
    a.add_collection(PatchCollection(pa,facecolor=colors[k],edgecolor='none',alpha=.85))
    a.plot([],[],color=colors[k],lw=6,label=f'{k}: {len(cells)} cells / {areas[k]:.1f} um²')
a.axhspan(129.6,133.92,color='red',alpha=.14,label=f'old proposed band: actual {s["old_proposed_band_fill_actual"]*100:.2f}% mass fill')
a.set(xlim=(-5,536.25),ylim=(-5,255),aspect='equal',xlabel='µm',ylabel='µm',title='CTRL 22 actual bank64 macros: placed diagnostic only\nFull-row DPL pass; band, source reset, CDC, native and parent proof remain open')
a.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3,fontsize=9)
f.tight_layout();f.savefig(p/'actual_placement.png',dpi=170);plt.close(f)
print(json.dumps(s,indent=2))
