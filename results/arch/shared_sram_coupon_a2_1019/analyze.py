import json,re,collections,hashlib,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;N=P/'native';c=json.loads((P/'coupon.json').read_text());ledger=json.loads((N/'native_shape_ledger.json').read_text())
def markers(path):
 out=[]
 for chunk in path.read_text().split('violation type: ')[1:]:
  mt=re.search(r'bbox = \(([-.\d]+), ([-.\d]+)\) - \(([-.\d]+), ([-.\d]+)\) on Layer (\S+)',chunk);assert mt
  out.append(dict(type=chunk.splitlines()[0],nets=re.findall(r'net:(\S+)',chunk.splitlines()[1]),bbox_nm=[round(float(v)*1000) for v in mt.groups()[:4]],layer=mt.group(5)))
 return out
rows=[]
for i,x in enumerate(c['cases']):
 mm=markers(N/f'roi_{i:02d}.rpt');tn={a['net'] for a in ledger if a['case']==i and a['source_net']==x['pin']};roi=x['score_roi_nm']
 # Native ROI markers retained as returned; inner bbox classification independent.
 inner=[a for a in mm if a['bbox_nm'][2]>=roi[0] and a['bbox_nm'][0]<=roi[2] and a['bbox_nm'][3]>=roi[1] and a['bbox_nm'][1]<=roi[3]]
 target=[a for a in inner if tn.intersection(a['nets'])]
 rows.append(dict(case=i,name=x['name'],family=x['family'],kind=x['kind'],pin=x['pin'],target_native_nets=sorted(tn),target_counts=dict(collections.Counter(a['type'] for a in target)),all_inner_counts=dict(collections.Counter(a['type'] for a in inner)),native_roi_counts=dict(collections.Counter(a['type'] for a in mm)),geometry_components=len(x['independent_geometry_components']),markers=mm,inner_markers=inner))
control={a['name']:a for a in rows if a['family']=='control'}
assert control['aligned_rectangle']['all_inner_counts']=={}
assert control['original_9nm_step']['target_counts'].get('Rect Only')==2
assert control['spacing_23nm']['all_inner_counts'].get('Metal Spacing')==1
assert control['disconnected_contact']['geometry_components']==2
img=json.loads((N/'image_inspect.json').read_text())[0];assert img['Id']=='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';assert(N/'binary_sha256.txt').read_text().split()[0]=='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'
raw=markers(N/'all_markers.rpt')
for marker in raw:
 marker['source_case_ids']=sorted({int(re.match(r'case(\d+)_',n).group(1)) for n in marker['nets']})
 marker['inside_own_score_ROI']=[]
 for ci in marker['source_case_ids']:
  roi=c['cases'][ci]['score_roi_nm'];b=marker['bbox_nm']
  if b[2]>=roi[0] and b[0]<=roi[2] and b[3]>=roi[1] and b[1]<=roi[3]:marker['inside_own_score_ROI'].append(ci)
assert len([v for v in raw if all(i<28 for i in v['source_case_ids'])])==15
assert not any(v['inside_own_score_ROI'] for v in raw if all(i<28 for i in v['source_case_ids']))
noncontrol=[a for a in rows if a['family']!='control'];result=dict(status='BOUNDED_VISIBLE_WIRE_A2_RESULT_ONLY',full_master_qualified=False,source_model_commit='c634d1540',source_input_commit='2825d2ba5',all_native_markers=raw,all_native_markers_count=len(raw),all_native_marker_types=dict(collections.Counter(a['type'] for a in raw)),representative_target_marker_totals=dict(collections.Counter(a['type'] for r in noncontrol for a in r['inner_markers'] if set(r['target_native_nets']).intersection(a['nets']))),cases=rows,coverage_HOLD=['Non-ORTH width-table DRT binding/import absent; native silence is not table qualification.','Track-phase native enforcement not established.','OBS identities retained as reservations only; own PG/OBS conflicts unresolved; no AP/PG route check.','Conditional core/contact/internalPG model has no fabricated/extracted transistor layout.','No native timing/RC, B/C, production LEF/Lib, full-master access, source phase, reset, K or first-use closure.'])
(P/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
fig,axes=plt.subplots(6,6,figsize=(21,20))
for ax,x,r in zip(axes.flat,c['cases'],rows):
 ox,oy=x['anchor_nm']
 for a in x['shapes']:
  b=a['rect_nm'];col='#126eac' if a['net']==x['pin'] else ('#bd6e21' if a.get('role')=='conditional_PG' else '#888888');ax.add_patch(Rectangle((b[0]-ox,b[1]-oy),b[2]-b[0],b[3]-b[1],facecolor=col,alpha=.65))
 for v in x['vias']:
  for k in ['m4_rect_nm','m5_rect_nm','cut_rect_nm']:
   b=v[k];ax.add_patch(Rectangle((b[0]-ox,b[1]-oy),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='#d5a000',linewidth=.7))
 for a in r['markers']:
  b=a['bbox_nm'];ax.add_patch(Rectangle((b[0]-ox,b[1]-oy),max(1,b[2]-b[0]),max(1,b[3]-b[1]),fill=False,edgecolor='red',linewidth=.7))
 ax.set(xlim=(-220,220),ylim=(-220,220),aspect='equal');ax.set_title(x['name']+'\n'+str(r['target_counts']),fontsize=6)
for ax in list(axes.flat)[len(rows):]:ax.axis('off')
fig.suptitle('A2 unrepaired native visible-wire coupon: exact c634 model crops, native returned ROI markers in red\nTarget marker counts scoped to inner ROI; raw crop-edge artifacts retained. No AP/PG/timing/full-master qualification.')
fig.tight_layout();fig.savefig(N/'coupon_a2_result.png',dpi=150)
print(json.dumps({k:result[k] for k in ['all_native_markers_count','all_native_marker_types','representative_target_marker_totals']}))
for r in rows:print(r['name'],r['target_counts'],r['all_inner_counts'],r['geometry_components'])
