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
fig.suptitle('A3 PREENGINE: complete master geometry, no crop, no translation, no repair\nM4 blue / M5 green / cuts gold / disconnected conditional PG orange / OBS reservation dashed purple (not metal)')
fig.tight_layout();fig.savefig(P/'A3_WHOLEMASTER_PREENGINE.png',dpi=180)
(P/'geometry_compare.json').write_text(json.dumps(proof,indent=2)+'\n')
(P/'PREENGINE_CHECKLIST.md').write_text('''# A3 before native execution

Exact c634 model SHA256 033b2a0e1522a9bd28b3ab9a35df88d394175fa06fbf6dca0e6f48b12e97146a. Independent comparison of every source-identified signal rectangle, complete native via enclosure/cut, PG rectangle and all OBS reservations against original model: zero differences. Full outline containment holds; no crop or translation. All 643 signal networks have one independent connected geometry component. Every complete via retains actual 24 nm cut and 46x24 / 24x46 nm enclosures. 206/437 signals, 408/870 vias, 44/77 PG, six OBS per master. First and last entries included by complete identity equality.

Full master plot differs from A2 representative scope: ROOT personal visual approval is REQUIRED before engine. Native execution remains stopped. Exact planned execution is three sequential processes, nine calls: each full master global + full-outline integer-DBU ROI; unchanged four controls global + four ROI calls. Global reports are verdicts. No outside-ROI classification or marker suppression. No automatic repair.

PG uses original VDD/VSS identities as regular visible SIGNAL dbWire diagnostic metal. It remains disconnected (Qwen 22/22 rail components; SC2 39/38), not electrically fed. All 121 PG/own-OBS access conflicts remain HOLD. All 12 OBS reservations retained as explicit model objects, not metal or hidden fixed pins. Native ODB shape/bounds/visibility comparison remains required before checker. No B/C, AP, PDN, production views, Liberty, timing, pin assignment, native track or non-ORTH width-table qualification.

R0 local origin only. 43.2 lattice, cell utilization, CTS insertion/spread, reset, first use, K, SU latency and timing are unmeasured and not claimed. Native source/technology hash, actual current image/binary inspection, host headroom and measured resources will be retained for execution. Proposed admission 1 CPU / 4 GiB / 2 GiB, based prior measured A2 receipt and 4407-object inventory scaling, with no guessed runtime deadline. Original A2 failures and controls remain immutable.
''')
print(json.dumps(proof,indent=2))
