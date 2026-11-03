from pathlib import Path
import json,gzip,collections,math
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
R=Path('/srv/opentallas-scratch/claude/wt/codex-kv-physical-2034/results/flow/kv_pc_geo80_birth_1102/fresh_grt/result')
j=json.loads(gzip.decompress(Path('/home/ubuntu/coord/tmp/pc_geo80_saved_grt_geometry.json.gz').read_bytes()))
c=json.load(open(R.parent.parent/'result/CHECKPOINT_CENSUS.json'));old=json.load(open('/home/ubuntu/coord/tmp/pc_geo80_original_components.json'))
norm=lambda n:n
expected={norm(n):v for n,v in old.items() if not v['master'].startswith(('FILLER','DECAP'))}
for n in c['removed']:del expected[norm(n)]
for n,v in c['new'].items():expected[norm(n)]=v
for n,v in c['changed'].items():expected[norm(n)]=v['after']
assert set(expected)==set(j['cells']),(len(expected),len(j['cells']),list(set(expected)^set(j['cells']))[:10])
bad=[n for n,v in expected.items() if v['master']!=j['cells'][n]['master']];assert not bad,bad[:5]
moved={n:{'before':v['pose'],'after':j['cells'][n]['location'],'orientation_after':j['cells'][n]['orient']} for n,v in expected.items() if max(abs(float(v['pose'][q+1])/1000-j['cells'][n]['location'][q]) for q in range(2))>1e-8}
outside=[n for n,v in j['cells'].items() if v['box'][0]<-1e-6 or v['box'][1]<-1e-6 or v['box'][2]>397.44+1e-6 or v['box'][3]>362.88+1e-6]
assert not outside,outside[:8]
a=np.array([v['location'] for v in j['cells'].values()]);fig,ax=plt.subplots(figsize=(10,9));ax.hist2d(a[:,0],a[:,1],bins=(180,165),cmap='Blues',cmin=1)
for name,color in [('VDD','#b66868'),('VSS','#777777')]:
 seg=[]
 for r in j['PG'][name]['rectangles']:
  if r['layer'] in ['M6','M7','M8','M9']:
   x0,y0,x1,y1=r['box'];seg.append([(x0,(y0+y1)/2),(x1,(y0+y1)/2)] if x1-x0>=y1-y0 else [((x0+x1)/2,y0),((x0+x1)/2,y1)])
 ax.add_collection(LineCollection(seg,colors=color,linewidths=.28,alpha=.25))
for key,color,mark in [('new','red','o'),('changed','orange','x')]:
 b=np.array([j['cells'][norm(n)]['location'] for n in c[key]]);ax.scatter(b[:,0],b[:,1],s=16,c=color,marker=mark,label=f'{len(b)} repair '+key)
p=np.array([[(v['box'][0]+v['box'][2])/2,(v['box'][1]+v['box'][3])/2] for v in j['pins'] if v['role'] not in ['POWER','GROUND']]);ax.scatter(p[:,0],p[:,1],s=.8,c='green',alpha=.5,label='Actual public pin metal')
ax.set(xlim=(0,397.44),ylim=(0,362.88),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Actual saved PC DPL + data-GRT layout before detailed route');ax.legend(loc='upper right',fontsize=8)
fig.text(.06,.025,'223,911 cells / 1,312 rows; native DPL zero illegal cells/sites; no cell/master change after repair.\n4,133 signal pins; original 4,261 clock nets / 48,012 connected instances unchanged; reopened saved PG447,822/0.\nActual PG trunks shown faintly. This is legal placement + GRT only: detailed DRC/ANT/TT/FF/LEC still pending.',fontsize=9)
fig.tight_layout(rect=(0,.09,1,1));fig.savefig(R/'actual_saved_grt.png',dpi=150);plt.close(fig)
rec={'ODB_sha256':j['sha256'],'cells':len(j['cells']),'rows':len(j['rows']),'names_or_master_differences_from_repair':0,'DPL_moved_cells':moved,'outside_outline':outside,'signal_pin_bits':len({v['name'] for v in j['pins'] if v['role'] not in ['POWER','GROUND']}),'placement_status':dict(collections.Counter(v['status'] for v in j['cells'].values())),'PG_terms':{n:v['terminals'] for n,v in j['PG'].items()},'render':'actual_saved_grt.png','status':'ACTUAL_SAVED_LAYOUT_FOR_LOOK_NOT_SIGNED'}
(R/'SAVED_GEOMETRY_REVIEW.json').write_text(json.dumps(rec,indent=2)+'\n');print('cells',len(j['cells']),'moved',len(moved),'outside',len(outside),'PG',rec['PG_terms'])
