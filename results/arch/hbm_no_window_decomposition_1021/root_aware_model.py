#!/usr/bin/env python3
"""Bounded model over emitted O placements, fixed original roots; no GEN/probe."""
import json,copy,hashlib,collections
from pathlib import Path
D=Path(__file__).parent;A=Path('/home/ubuntu/artifacts/hdie-d4/codex_hbm_r16o_corridor_1021/planoM');m=json.load(open(A/'case_a_manifest.json'));R=json.load(open(A/'root_sites.json'));orig=copy.deepcopy(m['placement'])
model=json.load(open(D.parent/'hbm_release_r16_1021/plano2M/corridor_model.json'));expected={r['instance']:r['after'] for r in model['placement_checks']}
xy={'svg_NW1':(9721.08,30937.04),'xc_NW1':(9497.952,31045.04),'xc_NW2':(10677.96,31194.3),'vmks_NW1':(10518.984,31390.64),'wbc_NW':(10630.4,31320.)}
for n in ['refcfg_SW','refcfg_NW','cij_SW','cij_SE','cij_NW','cij_NE']:xy[n]=(expected[n]['x'],expected[n]['y'])
for n,(x,y) in xy.items():m['placement'][n].update(x=x,y=y)
def box(v):
 w,h=v['w'],v['h']
 if v.get('o') in ['R90','R270','MXR90','MYR90']:w,h=h,w
 return [v['x'],v['y'],v['x']+w,v['y']+h]
def inter(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6
def contains(a,x,y):return a[0]<x<a[2] and a[1]<y<a[3]
B={n:box(v) for n,v in m['placement'].items() if not n.startswith('rly') and not v['m'].startswith('hbfd_rly')};carves=[]
for n,v in m['placement'].items():
 if n not in B:continue
 for c in m.get('carved_feedthrough',{}).get(v['m'],[]):
  x,z=c['x_um'];y,t=c['y_um'];o=v.get('o','R0')
  if o in ['MY','R180']:x,z=v['w']-z,v['w']-x
  if o in ['MX','R180']:y,t=v['h']-t,v['h']-y
  carves.append((n,[v['x']+x,v['y']+y,v['x']+z,v['y']+t],c))
contacts=[]
for s in R['sites']:
 q=s['keepout'];bc=[n for n,b in B.items() if inter(q,b)];cc=[{'instance':n,'box':b,'source_kind':c['kind'],'owner':c.get('owner'),'keepout_rule':c.get('master_keepout')} for n,b,c in carves if inter(q,b)];center=[n for n in bc if contains(B[n],s['x'],s['y'])];center_carves=[a for a in cc if contains(a['box'],s['x'],s['y'])]
 # Exact continuous rectangle union integration of body minus global model carve.
 xs=sorted({q[0],q[2]}|{max(q[0],min(q[2],z)) for n in bc for z in [B[n][0],B[n][2]]}|{max(q[0],min(q[2],z)) for a in cc for z in [a['box'][0],a['box'][2]]});ys=sorted({q[1],q[3]}|{max(q[1],min(q[3],z)) for n in bc for z in [B[n][1],B[n][3]]}|{max(q[1],min(q[3],z)) for a in cc for z in [a['box'][1],a['box'][3]]});solid=0
 for x,z in zip(xs,xs[1:]):
  for y,t in zip(ys,ys[1:]):
   px,py=(x+z)/2,(y+t)/2
   if any(contains(B[n],px,py) for n in bc) and not any(contains(a['box'],px,py) for a in cc):solid+=(z-x)*(t-y)
 old=next((n for reg,n in R['inside_blocks'] if reg==s['region']),None)
 status=('SOURCE_CENTER_IN_PLANNED_CHANNEL_RESERVATION_OVERLAP_PHYSICAL_OPEN' if center_carves else 'CENTER_IN_FIXED_SOLID_BODY_PHYSICAL_CONFLICT_OPEN') if center else ('CENTER_CLEAR_RESERVATION_BODY_CONTACT_OPEN' if bc else 'MODEL_BODY_CLEAR_REAL_CLOCK_PROOF_OPEN')
 contacts.append(dict(region=s['region'],root=[s['x'],s['y']],keepout=q,root_ownership_unchanged=True,original_first_bbox_report=old,all_body_keepout_contacts=bc,center_inside_bodies=center,planned_channel_contacts=cc,center_in_model_carve=bool(center_carves),solid_body_area_in_keepout_um2=round(solid,6),disposition=status,rule='d4g_root_sites says roots must sit in channels; failed=[] is reporting-only, not a waiver. Geometric carve is a source planning promise, not independent physical clock-cell permission.'))
changes=[]
for n in xy:
 bad=[k for k,b in B.items() if k!=n and inter(B[n],b)];roots=[s['region'] for s in R['sites'] if inter(B[n],s['keepout'])];assert not bad and not roots,(n,bad,roots)
 changes.append(dict(instance=n,before=orig[n],after=m['placement'][n],body_overlap_contacts=bad,fixed_root_keepout_contacts=roots,source_params_ports_clock_reset_change=False))
r={'status':'ONE_ROOT_AWARE_LOCAL_SOURCE_MODEL_ONLY_NOT_SELECTED_NO_ADMISSION','basis_O':'83d057be0 actual67 preserved','supersedes_local_northstack':'d0164d2b2 OPEN proposal retained, not executed','clock_root_source_sha256':hashlib.sha256((A/'root_sites.json').read_bytes()).hexdigest(),'roots_moved_or_relabelled':0,'changed_bodies':changes,'all_45_root_contacts':contacts,'all_31_original_inside_block_reports_retained':sum(x['original_first_bbox_report'] is not None for x in contacts),'root_status_counts':dict(collections.Counter(x['disposition'] for x in contacts)),'reserved_reset_areas':m['reserved_reset_homes'],'reservation_scope':'All45 original clock root keepouts + all emitted non-relay bodies + emitted reserved reset sites(empty). No new physical reserved/contact witness inferred. Generated relay/forest homes must be replanned by ordinary authorized GEN; none admitted.','GLOBAL_FIT_QUALIFIED':False,'global_open_constraints':'Remaining unchanged root/body conflicts require explicit source/physical disposition; local11-body clearance is not a global root-clear claim. PHY and other hard-body center collisions cannot be waived or silently carved.','demand_improvement_measured':False,'new_GEN_S2_physical_probe_route':0}
(D/'root_aware_model.json').write_text(json.dumps(r,indent=2)+'\n');print('Local11body/rootcontact PASS; original31reports retained; globalfit NOTQUALIFIED',r['root_status_counts'])
