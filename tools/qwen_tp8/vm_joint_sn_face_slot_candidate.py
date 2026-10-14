"""Exact bbox feasibility of proposed g1 N-face EN1 diagnostic slots."""
import json, re, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]; BASE=R/'results/arch/qwen_tp8_1012'
P=json.load(open(BASE/'vm_leaf_plan_claude.json'));T=json.load(open(BASE/'vm_bay_tiles_claude.json')); G=json.load(open(BASE/'vm_rg6.json')); refs=dict(zip(G['core_names'],G['children'][:72])); boxes=[]; hashes={}
def size(view):
 f=next((R/view).glob('*.lef')); hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest();return list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',f.read_text()).groups()))
for c in P['children']:
 if c.get('region')==1:
  v=refs[c['n'].replace('vm_g1_','vm_g6_')]['view']; w,h=size(v);assert abs(w-c['w'])<1e-6 and abs(h-c['h'])<1e-6;boxes.append([c['x'],c['y'],c['x']+w,c['y']+h,c['n']])
views={'E':'physical/ref_tile/qfd_vm_xrelay_t/views/ot_qfd_vm_xrelay_t','W':'physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_w','P':'physical/ref_tile/qfd_vm_xpad2_t/views/ot_qfd_vm_xpad2_t'}
for bay in P['x_relay_bays']:
 if bay.get('region')==1:
  for t in T['bay_tiles'].get(bay['n'],[]):
   w,h=size(views[t['kind']]);x,y=bay['x']+t['slot']*21.6,bay['y'];boxes.append([x,y,x+w,y+h,bay['n']+'_t'+str(t['slot'])])
assert len(boxes)==152
stations=[dict(name='g1_sn_exit1',at_um=[15318.72,18115.92]),dict(name='g1_sn_exit2',at_um=[15450.48,18115.92])]
collisions=[]
for st in stations:
 x,y=st['at_um'];st.update(outline_um=[129.6,12.96],master='ot_qfd_vm_face_sn_e1',d_face='S',q_face='N',clock_pin='clk',engine_early_pin='me_e');
 for a,b,A,B,n in boxes:
  if x<A+2.16-1e-6 and x+129.6>a-2.16+1e-6 and y<B+2.16-1e-6 and y+12.96>b-2.16+1e-6:collisions.append([st['name'],n])
 boxes.append([x,y,x+129.6,y+12.96,st['name']])
for f in [BASE/'vm_leaf_plan_claude.json',BASE/'vm_bay_tiles_claude.json',BASE/'vm_rg6.json']:hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
a=dict(schema='opentallas.vm-sn-face-slot-candidate.v1',status='DIAGNOSTIC_SLOT_PURPOSE_ONLY_NOT_FROZEN',region=1,source_prototype_commit='05fc106df',proposed_engine_edges_added=1,proposed_total_XPR_with_one_added_band_edge=14,purpose='Replace rejected tall W regional exit stations, not add another pipeline edge. All688 exact old source-to-SN and SN-to-band paths still require actual ETM mapping and DATA RC. These N slots do not claim an S slot fits12.96um.',existing_masters_preserved=152,geometry_gap_um=2.16,geometry_collisions=collisions,outer_N_gap_um=2.16,source_hashes=hashes,stations=stations,assigned_pins=None,actual_normalized_endpoint_data=None)
(BASE/'vm_joint_g1_sn_face_slot_candidate.json').write_text(json.dumps(a,indent=1)+'\n');print('collisions',collisions)
