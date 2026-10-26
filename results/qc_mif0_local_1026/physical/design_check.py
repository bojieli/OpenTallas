from pathlib import Path
import csv,json,re,math,gzip
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=Path(__file__).resolve().parent
norm=lambda s:s.replace('\\','')
D=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
summary={}
fig,axs=plt.subplots(1,2,figsize=(13,5))
for typ,ax in zip(['prog','btab'],axs):
 rows=list(csv.DictReader(gzip.open(ROOT/(typ+'_fullhalf_place.csv.gz'),'rt')))
 pins={norm(r['name']):(float(r['x']),float(r['y'])) for r in rows if r['kind']=='pin'}
 ffs={norm(r['name']):(float(r['x']),float(r['y'])) for r in rows if r['kind']=='ff'}
 mappings=[]
 for line in open(ROOT/(typ+'_actual_macro_inputs.tsv')):
  macro,pin,x,y,old_dist,target=line.rstrip().split('\t');macro=norm(macro)
  if not pin.startswith(('r_ce','r_addr')):continue
  bank=int(re.search(r'\[(\d+)\]',macro)[1]);slot=bank*2+(0 if macro.endswith('u_lo') else 1) if typ=='prog' else bank
  ibit=int(re.search(r'\[(\d+)\]',pin)[1]) if '[' in pin else None
  sources=([f'p_idx[{ibit+1}]'] if ibit is not None else ['p_re','p_idx[0]']) if typ=='prog' else ([f'bs_addr[{ibit+2}]'] if ibit is not None else ['bs_re','bs_addr[0]','bs_addr[1]'])
  # Proposed face columns and legal row grid, not a placed candidate.
  rise=(346.140-1.188*slot,(81.270+.270*ibit if ibit is not None else 84.240)) if typ=='prog' else (346.140-1.188*slot,(96.390+.270*ibit if ibit is not None else 101.250))
  fall=ffs[norm(target.split('|')[0])];mp=(float(x),float(y))
  rec=dict(macro=macro,pin=pin,source_ports=sources,source_xy=[pins[s] for s in sources],proposed_rise_xy=rise,proposed_fall_xy=fall,actual_macro_pin_xy=mp,face_max_um=max(D(pins[s],rise) for s in sources),halfcycle_endpoint_um=D(rise,fall),macro_F6_um=D(fall,mp))
  mappings.append(rec)
  ax.plot([rise[0],fall[0]],[rise[1],fall[1]],color='#2376a9',alpha=.18,lw=.7)
  ax.scatter(*rise,c='#bd5427',s=8);ax.scatter(*fall,c='#2376a9',s=8)
 for r in rows:
  if r['kind']=='macro':
   from matplotlib.patches import Rectangle
   ax.add_patch(Rectangle((float(r['x']),float(r['y'])),float(r['w']),float(r['h']),fc='#ddd',ec='#555'))
 for name,xy in pins.items():
  if name.startswith(('p_idx','p_re','bs_addr','bs_re')):ax.scatter(*xy,c='#111',s=4)
 ax.set_title(typ.upper()+' proposed FACE rising → macro falling\nblue paths are half-cycle; geometry only')
 ax.set_xlabel('µm');ax.set_ylabel('µm');ax.set_aspect('equal');ax.grid(alpha=.15)
 summary[typ]=dict(count=len(mappings),face_max_um=max(r['face_max_um'] for r in mappings),halfcycle_max_um=max(r['halfcycle_endpoint_um'] for r in mappings),halfcycle_min_um=min(r['halfcycle_endpoint_um'] for r in mappings),macro_F6_max_um=max(r['macro_F6_um'] for r in mappings),over405=sum(r['halfcycle_endpoint_um']>405 for r in mappings),face_over20=sum(r['face_max_um']>20 for r in mappings),macro_over20=sum(r['macro_F6_um']>20 for r in mappings),mappings=mappings)
(OUT/'proposed_read_bindings.json').write_text(json.dumps(summary,indent=2)+'\n')
fig.tight_layout();fig.savefig(OUT/'proposed_read_bindings.png',dpi=160)
print(json.dumps({t:{k:v for k,v in x.items() if k!='mappings'} for t,x in summary.items()},indent=2))
