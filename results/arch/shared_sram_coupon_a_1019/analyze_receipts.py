#!/usr/bin/env python3
"""Bounded native marker/ROI reporting; never repairs geometry or suppresses raw markers."""
import collections,hashlib,json,re,textwrap
from pathlib import Path
P=Path(__file__).resolve().parent
coupon=json.loads((P/'coupon.json').read_text());ledger=json.loads((P/'native/native_shape_ledger.json').read_text())
def markers(path):
 text=path.read_text();out=[]
 for chunk in text.split('violation type: ')[1:]:
  lines=chunk.splitlines();m=re.search(r'bbox = \(([-.\d]+), ([-.\d]+)\) - \(([-.\d]+), ([-.\d]+)\) on Layer (\S+)',chunk)
  assert m,(path,chunk)
  out.append(dict(type=lines[0],nets=re.findall(r'net:(\S+)',lines[1]),bbox_nm=[round(float(v)*1000) for v in m.groups()[:4]],layer=m.group(5)))
 return out
allmarkers=markers(P/'native/all_markers.rpt');rows=[]
for i,c in enumerate(coupon['cases']):
 mm=markers(P/f'native/roi/roi_{i:02d}.rpt');target={a['net'] for a in ledger if a['case']==i and a['source_net']==c['pin']}
 tm=[m for m in mm if target.intersection(m['nets'])]
 row=dict(case=i,name=c['name'],family=c['family'],pin=c['pin'],pin_kind=c.get('pin_kind'),face=c.get('face'),native_wire_status=c['wire_status'],score_roi_nm=c['score_roi_nm'],all_roi_counts=dict(collections.Counter(m['type'] for m in mm)),actual_target_counts=dict(collections.Counter(m['type'] for m in tm)),target_native_nets=sorted(target),geometry_components=len(c['independent_geometry_components']),markers=mm)
 if c['family']!='control' and c['kind']=='source':assert row['actual_target_counts'].get('Rect Only')==2,row
 rows.append(row)
assert rows[10]['all_roi_counts']=={}
assert rows[11]['all_roi_counts'].get('Rect Only')==2
assert rows[12]['all_roi_counts'].get('Rect Only')==2 # FIXED dbWire is still routed polygon to GC.
assert rows[13]['all_roi_counts'].get('Metal Spacing')==1
assert rows[14]['geometry_components']==2
assert rows[15]['all_roi_counts']=={} and rows[16]['all_roi_counts']=={}
fixed=markers(P/'native/fixed_pin/fixed_pin_markers.rpt');assert fixed==[]
resources=[]
for sub in ['native','native/roi','native/fixed_pin']:
 text=(P/sub/'resources.time').read_text();resources.append(dict(path=sub,elapsed=re.search(r'Elapsed .*: (\S+)\n',text).group(1),peak_rss_kib=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',text).group(1)),disk_bytes=int((P/sub/'disk.bytes').read_text().split()[0])))
result=dict(status='NATIVE_VISIBLE_SOURCE_JOIN_RECTONLY_FAIL_BOTH_FAMILIES',production_qualified=False,stages_B_C_run=False,original_geometry_repaired=False,image_digest='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29',binary_sha256='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846',version='26Q3-1510-g6cb3f2b704',original_full_marker_counts=dict(collections.Counter(m['type'] for m in allmarkers)),original_full_marker_count=len(allmarkers),cases=rows,true_fixed_pin_marker_counts={},resources=resources,coverage_gaps=['Native non-ORTH WIDTHTABLE import absent; 33nm control silence is not legal width.','Native old-track phase control silence is not global track qualification.','No sub-grid control can be represented at integer1nm DBU/manufacturing grid.','Whole-chip crop-edge width/area artifacts retained, not treated as source-join verdicts.','Via crop silence qualifies neither all master vias nor PG nor AP/route.','dbWire FIXED status does not create GC fixed polygons; true fixed BPin is the silent visibility negative.','Actual native FF/SS timing, K, reset, lifecycle, source phase and full-token release remain unqualified.'])
(P/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','original_full_marker_counts','resources']}))
# Plot exact native-input ledger and complete native markers, not a fabricated route image.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,axes=plt.subplots(4,5,figsize=(19,14))
for i,ax in enumerate(axes.flat):
 if i>=len(rows):ax.axis('off');continue
 c=coupon['cases'][i];x,y=c['anchor_nm'];roi=c['score_roi_nm']
 for a in ledger:
  if a['case']!=i:continue
  if 'rect_nm' in a:
   r=a['rect_nm'];col='#1678b0' if a['source_net']==c['pin'] or (c['family']=='control' and a['source_net']=='a') else '#aaaaaa'
   ax.add_patch(Rectangle((r[0]-x,r[1]-y),r[2]-r[0],r[3]-r[1],facecolor=col,alpha=.65,edgecolor='black',linewidth=.3))
  else:
   for b in a['native_boxes']:
    r=b['rect_nm'];ax.add_patch(Rectangle((r[0]-x,r[1]-y),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='#d39500',linewidth=.8))
 for m in rows[i]['markers']:
  r=m['bbox_nm'];ax.add_patch(Rectangle((r[0]-x,r[1]-y),max(1,r[2]-r[0]),max(1,r[3]-r[1]),fill=False,edgecolor='red',linewidth=1))
 ax.set(xlim=(-220,220),ylim=(-220,220),aspect='equal',xlabel='nm from exact anchor',ylabel='nm')
 ax.set_title(c['name']+'\n'+'\n'.join(textwrap.wrap(str(rows[i]['all_roi_counts']),45)),fontsize=7)
fig.suptitle('Stage A original unrepaired native wire coupon: exact dbWire ledger; native ROI markers in red',fontsize=15);fig.tight_layout();fig.savefig(P/'native/coupon_a.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(6,4))
for r in json.loads((P/'native/fixed_pin/fixed_pin_geometry.json').read_text())['rects_nm']:
 ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],facecolor='#886ab5',alpha=.6))
ax.set(xlim=(700,1100),ylim=(950,1060),aspect='equal',xlabel='native DBU (nm)',ylabel='native DBU (nm)',title='True fixed BPin: same 9nm union, 0 native markers\nVisibility negative only; not geometry qualification');fig.tight_layout();fig.savefig(P/'native/fixed_pin/fixed_pin.png',dpi=180);plt.close(fig)
manifest={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.rglob('*')) if f.is_file() and f.name!='SHA256.json'}
(P/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
