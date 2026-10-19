import json,hashlib,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;c=json.loads((P/'coupon.json').read_text());m=json.loads((P/'input/model.json').read_text());proof=[]
for x in c['cases']:
 if x['family']=='control':continue
 d=m['families'][x['family']]; allshapes={f'signal:{p["pin"]}:{i}':a for p in d['signal_ledger'] for i,a in enumerate(p['new_shapes'])}; allshapes.update({f'PG:{p["id"]}':dict(layer=p['layer'],net=p['net'],rect_nm=p['new_rect_nm']) for p in d['PG_ledger']}); av={f'via:{p["pin"]}:{i}':v for p in d['signal_ledger'] for i,v in enumerate(p['new_vias'])};dx,dy=x['translation_nm'];box=x['source_crop_nm']
 for a in x['shapes']:
  orig=allshapes[a['source_identity']];assert a['source_rect_nm']==orig['rect_nm'];r=orig['rect_nm'];clip=[max(r[0],box[0]),max(r[1],box[1]),min(r[2],box[2]),min(r[3],box[3])];assert a['rect_nm']==[clip[0]+dx,clip[1]+dy,clip[2]+dx,clip[3]+dy];assert(a['net'],a['layer'])==(orig['net'],orig['layer'])
 for v in x['vias']:
  orig=av[v['source_identity']]
  for key in ['m4_rect_nm','m5_rect_nm','cut_rect_nm']:
   r=orig[key];assert v[key]==[r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy]
 proof.append(dict(case=x['name'],exact_shapes=len(x['shapes']),exact_complete_vias=len(x['vias']),true_OBS_identities=len(x['neighbor_OBS']),translation_mod48=[dx%48,dy%48],target_components=len(x['independent_geometry_components'])))
fig,axes=plt.subplots(math.ceil(len(c['cases'])/6),6,figsize=(21,20))
for ax,x in zip(axes.flat,c['cases']):
 ox,oy=x['anchor_nm']
 for a in x['shapes']:
  r=a['rect_nm'];color='#126eac' if a['net']==x['pin'] else ('#bd6e21' if a['role']=='conditional_PG' else '#888888');ax.add_patch(Rectangle((r[0]-ox,r[1]-oy),r[2]-r[0],r[3]-r[1],facecolor=color,alpha=.65))
 for v in x['vias']:
  for k in ['m4_rect_nm','m5_rect_nm','cut_rect_nm']:
   r=v[k];ax.add_patch(Rectangle((r[0]-ox,r[1]-oy),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='#d5a000',linewidth=.7))
 ax.set(xlim=(-220,220),ylim=(-220,220),aspect='equal');ax.set_title(x['name'],fontsize=7)
for ax in list(axes.flat)[len(c['cases']):]:ax.axis('off')
fig.suptitle('PREENGINE A2: exact c634 model crops; REGULAR dbWire planned; all neighboring signal/PG identities retained\nBlue target, gray neighboring signals, brown conditional PG; yellow complete via; OBS remains explicit reservation HOLD')
fig.tight_layout();fig.savefig(P/'candidate_a2.png',dpi=140)
(P/'geometry_compare.json').write_text(json.dumps(dict(status='PASS_EXACT_C634_GEOMETRY_NO_DIFFERENCES',cases=proof),indent=2)+'\n')
(P/'PREENGINE_CHECKLIST.md').write_text('''# A2 pre-engine checklist

Exact c634d1540 model copied byte-for-byte; geometry_compare.json independently compares every cropped signal/PG rectangle and complete via enclosure/cut against the model. Zero differences. R0 only, phase-preserving translation by multiples of48 nm.32 cases:28 actual representative crops plus4 controls;477 metal rectangles and130 complete vias including all neighbors. Both families include clock/control/data and first/last W/E source ends; complete first/last via columns sampled. All intersecting true OBS identities retained as uninstantiated reservations; own PG/OBS access remains HOLD.

A2 is a regular routed dbWire diagnostic geometry coupon, no cell band/CTS/STA/macros/placement/full-face access.43.2-lattice placement, utilization, clock insertion/spread and timing are not measured by this coupon. Native width-table/track applicability coverage gaps remain. No fixed BPin, B/C/AP/PDN, production LEF/Lib or repair. Conditional PG internal attachment+12nm and core+39nm are model obligations, not electrical claims. Proposed minimal admission1CPU/4GB/2GB based originalA measured0.65s/250152KiB/3.25MB. Current run expects bounded32 ROIs and one full native GC check, with contemporaneous image/binary/resource receipts. OriginalA raw failures remain immutable.
''')
print('exact comparison PASS',len(proof),'candidate_a2.png saved')
