# PATH-QC-SRAMIF2 render of 3_place: placed.csv + r2r_3_place.json worst links
import sys,csv,json,re
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
K,title,out=sys.argv[1:4]
rows=list(csv.DictReader(open(K+'/placed.csv'))); r2=json.load(open(K+'/r2r_3_place.json'))
pos={x['name']:(float(x['x'])+float(x['w'])/2,float(x['y'])+float(x['h'])/2) for x in rows}
fig,axs=plt.subplots(1,2,figsize=(22,9))
cat=lambda n:('IF(g_r)' if '.g_r.' in n else 'rd capture' if re.match(r'^(pcap|bcap|rcap)',n) else 'pin reg' if re.match(r'^(p|pbs|ptw|pp|bs_q|p_q|ptw)',n) else 'other ff')
cols={'IF(g_r)':'red','rd capture':'magenta','pin reg':'green','other ff':'tab:blue'}
for ax,zoom in zip(axs,(False,True)):
  ax.add_patch(plt.Rectangle((0,0),354.24,259.2,fill=False))
  for kind,col,s in (('std','0.8',0.3),('buf','orange',0.5)):
    r=[x for x in rows if x['kind']==kind]; ax.scatter([float(x['x']) for x in r],[float(x['y']) for x in r],s=s,c=col,lw=0)
  ffs=[x for x in rows if x['kind']=='ff']
  for c,col in cols.items():
    r=[x for x in ffs if cat(x['name'])==c]; ax.scatter([float(x['x']) for x in r],[float(x['y']) for x in r],s=1.5 if not zoom else 4,c=col,lw=0,label=f'{c} {len(r)}')
  for x in rows:
    if x['kind']=='macro': ax.add_patch(plt.Rectangle((float(x['x']),float(x['y'])),float(x['w']),float(x['h']),color='k',alpha=.2))
  for w in r2['worst']:
    a=pos.get(w['launch'].replace('\\\\','\\')) or pos.get(w['launch']); b=pos.get(w['capture'])
    if a and b: ax.plot([a[0],b[0]],[a[1],b[1]],lw=.6,c='k')
  ax.set_aspect('equal')
  if zoom: ax.set_xlim(60,160); ax.set_ylim(20,90); ax.set_title('zoom: SRAM0 W face')
  else: ax.set_title(title+f"\nr2r max {r2['max']:.1f} p99 {r2['p99']:.1f} >290:{r2['gt290']} >405:{r2['gt405']} (black = worst 20)"); ax.legend(loc='upper left',markerscale=4,fontsize=8)
fig.tight_layout(); fig.savefig(out,dpi=100)
