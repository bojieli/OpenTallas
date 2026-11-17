#!/usr/bin/env python3
"""Analytically compose exact-source measured frame classes onto selected planned-instance lanes."""
import json,hashlib,sys,os,re,copy,shutil
from pathlib import Path
r=Path('/tmp/token_ds_followthrough1116'); root=r/'tapfix_source';code=r/'source';out=r/'tapfix_profiles';out.mkdir(exist_ok=True)
sys.path[:0]=[str(code/'tools/s81_dv'),str(code/'tools/die_plan'),str(code/'tools/s81_dv/layer_prog')]
import frame_schedule_asb as F
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=json.loads((root/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text());old=json.loads((r/'f2s4_source/physical/die_plan/s81/bind/frame_asbuilt.json').read_text());assert a==old,'selected manifest changed; new component required'
planpath=root/'selected_plan.json';p=json.loads(planpath.read_text());os.environ['OT_S81_FRAME_PLAN']=str(planpath)
F.SROOT[0]=root; F.SRC[0]=root;F.MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json'
die='\n'.join((root/f).read_text() for f in a['netlist']);typ={x['name']:p['partition_types'][x['type']] for x in p['partitions']}
def sig(parts):
 ret=[]
 for band,part in sorted(parts.items()):
  t=typ[part]
  params={k:v for k,v in t.get('param_set',{}).items() if not k.endswith('_INSTANCE')}
  contents=[{k:c.get(k) for k in ['inst','module','params']} for c in t['contents']]
  ret.append(dict(band=band,contents=contents,params=params))
 return ret
refs=[('u_f_0L02','fsa_h9_p2'),('u_f_0R02','fsa_h9_p5r2'),('u_f_0L03','fsa_h9_nx'),('u_f_0L01','fsa_h10_x')];templates={};rows=[]
for frame,run in refs:
 rr=r/run; sp=next(rr.glob('*schedule.json'));s=json.loads(sp.read_text());master=sp.name.removesuffix('_schedule.json');m,var=master.split('_l4_lp_asb_');parts=F.selected_frame_parts(p,a,frame,master,die);depth=F.bound_seam_depths(p,m,set(parts.values()))
 for f,h in s['source_sha256'].items():
  if f!=F.MANIFEST:assert sha(root/f)==h,('measured source changed',f)
 src={f:sha(root/f) for f in s['source_sha256']};F.BOUND_EXTRA.clear();F.BOUND_EXTRA.update({k:v-2 for k,v in depth.items() if v>2})
 assert depth==s['bound_plan']['seam_depths'],('new seam class requires retrace',frame,depth)
 lp=json.loads((root/F.LP_SCHED.format(m=m)).read_text());pm=json.loads((root/F.PLAN_MAP.format(m=m)).read_text())
 # Re-run the existing analytical schedule/plan comparison from immutable measured endpoints.
 mv=json.loads((rr/'work'/('validate_'+m+'_l4_lp.meas.json')).read_text());mt=json.loads((rr/'work'/(m+'_l4_lp.meas.json')).read_text());ma=json.loads((rr/'work'/(master+'.meas.json')).read_text())
 sched,links,checks,fails=F.schedule(mv,mt,ma,lp,pm,m,var,src,set(parts.values()));assert not fails,fails
 sched['selected_station_variants']=s['selected_station_variants'];sched['source_root']=str(root)
 key=(master,tuple(sorted(depth.items())));templates[key]=(sched,sig(parts),json.loads(next(rr.glob('*check.json')).read_text()),frame,sha(sp),checks,links)
for master,frame in sorted(re.findall(r'\b(col_h(?:9|10)_l4_lp_asb_(?:nx|x))\s*(?:#\s*\([^;]*?\)\s*)?([A-Za-z_]\w*)\s*\(',die)):
 m=master.split('_l4_lp_asb_')[0];parts=F.selected_frame_parts(p,a,frame,master,die);depth=F.bound_seam_depths(p,m,set(parts.values()));key=(master,tuple(sorted(depth.items())));sched,signature,check,ref,refsha,checks,links=templates[key];assert sig(parts)==signature,('numeric source profile differs',frame)
 s=copy.deepcopy(sched);s['bound_plan']=dict(plan=str(planpath),plan_sha256=sha(planpath),seam_depths=depth,seam_extra_stages={k:v-2 for k,v in depth.items() if v>2},control_seam_offset=None,frame_instance=frame,frame_parts=parts,frame_master=master,basis='PLANNED analytic seam composition; no terminal bind claim')
 s['analytical_replication']=dict(reference_frame=ref,reference_schedule_sha256=refsha,source_identity='every measured source hash plus normalized manifest exactly equal',numeric_band_signature_sha256=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest(),method='same measured source endpoint dates plus exact instance plan seams; source/plan checker rerun per class')
 d=out/'frames'/frame;d.mkdir(parents=True,exist_ok=True);sp=d/(master+'_schedule.json');sp.write_text(json.dumps(s,indent=1)+'\n');check=copy.deepcopy(check);check.update(schedule_sha256=sha(sp),bound_plan=s['bound_plan'],plan_consistency=checks,links=links,analytical_replication=s['analytical_replication']);(d/(master+'_check.json')).write_text(json.dumps(check,indent=1)+'\n');rows.append(dict(frame=frame,master=master,parts=parts,depth=depth,reference=ref,schedule_sha256=sha(sp)))
assert len(rows)==72,len(rows)
shutil.copy2(r/'gb_component/qualification/gb_provider_qualification.json',out/'gb_provider_qualification.json')
rec=dict(schema='opentallas.s81.planned-frame-composition.v1',status='PLANNED_SOURCE_AND_CALENDAR_COMPOSITION',source_plan_sha256=sha(planpath),manifest_identical=True,classes=len(templates),frames=rows,physical_bind_qualified=False,full_layer_compiled=False)
(out/'composition.json').write_text(json.dumps(rec,indent=1)+'\n');print('PLANNED_COMPOSITION_PASS classes',len(templates),'frames',len(rows),'plan',sha(planpath))
