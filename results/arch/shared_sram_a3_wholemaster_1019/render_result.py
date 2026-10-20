import gzip,json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent
raw=(P/'input/model.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='033b2a0e1522a9bd28b3ab9a35df88d394175fa06fbf6dca0e6f48b12e97146a'
m=json.loads(raw); inv=json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes())); proof={}
fig,axes=plt.subplots(2,1,figsize=(20,12))
for ax,(fam,d) in zip(axes,inv['families'].items()):
 src=m['families'][fam]; expected={}
 for p in src['signal_ledger']:
  for i,s in enumerate(p['new_shapes']):expected[f'{fam}:signal:{p["pin"]}:{i}']=(s['layer'],s['net'],s['rect_nm'])
  for i,v in enumerate(p['new_vias']):
   for layer,k in [('M4','m4_rect_nm'),('M5','m5_rect_nm'),('V4','cut_rect_nm')]:expected[f'{fam}:via:{p["pin"]}:{i}:{layer}']=(layer,v['net'],v[k])
 for s in src['PG_ledger']:expected[f'{fam}:PG:{s["id"]}']=(s['layer'],s['net'],s['new_rect_nm'])
 actual={s['identity']:(s['layer'],s['net'],s['rect_nm']) for s in d['shapes']};assert actual==expected
 assert [dict(s,identity=f'{fam}:OBS:{i}',interpretation='conditional reservation, NOT real metal and NOT hidden')for i,s in enumerate(src['new_reserved_OBS'])]==d['conditional_OBS']
 w,h=d['outline_nm'];assert all(0<=r[2][0]<r[2][2]<=w and 0<=r[2][1]<r[2][3]<=h for r in actual.values())
 proof[fam]={'comparison':'EXACT_ZERO_DIFFERENCES','boxes':len(actual),'counts':d['counts'],'outline_nm':[w,h],'R0_origin_nm':[0,0],'all_signal_components_one':all(n['component_count']==1 for n in d['geometry_networks'] if n['net'] not in ['VDD','VSS']),'OBS_unchanged':len(d['conditional_OBS'])}
 for layer,col in [('M4','#1274a8'),('M5','#36a87a'),('V4','#d89910')]:
  patches=[Rectangle((s['rect_nm'][0]/1000,s['rect_nm'][1]/1000),(s['rect_nm'][2]-s['rect_nm'][0])/1000,(s['rect_nm'][3]-s['rect_nm'][1])/1000) for s in d['shapes'] if s['layer']==layer and s['role']!='conditional_PG'];ax.add_collection(PatchCollection(patches,facecolor=col,alpha=.7,linewidth=0))
 for s in d['shapes']:
  if s['role']=='conditional_PG':
   r=s['rect_nm'];ax.add_patch(Rectangle((r[0]/1000,r[1]/1000),(r[2]-r[0])/1000,(r[3]-r[1])/1000,facecolor='#c94f28',linewidth=0))
 for s in d['conditional_OBS']:
  r=s['rect_nm'];ax.add_patch(Rectangle((r[0]/1000,r[1]/1000),(r[2]-r[0])/1000,(r[3]-r[1])/1000,fill=False,edgecolor='#9a2b9f',linestyle='--',linewidth=.8))
 ax.set(xlim=(-.2,w/1000+.2),ylim=(-.2,h/1000+.2),aspect='equal',xlabel='um',ylabel='um',title=f'{fam}: entire unchanged c634 master {w/1000:.3f} x {h/1000:.3f} um; {len(actual)} metal/cut boxes; {len(d["conditional_OBS"])} OBS reservations')
fig.suptitle('A3 RESULT: full GLOBAL native markers Qwen = 0 / SC2 = 0; full-outline ROIs agree; exact original controls retained\nCovered-rule result only. PG disconnected / OBS access HOLD; native WIDTHTABLE and track coverage gaps; no AP/PG/timing qualification')
fig.tight_layout();fig.savefig(P/'A3_WHOLEMASTER_RESULT.png',dpi=180)
