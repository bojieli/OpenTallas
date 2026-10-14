#!/usr/bin/env python3
"""Candidate registered-export pockets against all existing regional geometry.
This does not grant regional slots. Virtual-control reservation policy unresolved.
"""
import collections,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 lf=A/'vm_leaf_plan_claude.json';tf=A/'vm_bay_tiles_claude.json';jf=A/'vm_band_joint_region_candidate_input_codex.json';p=json.loads(lf.read_text());t=json.loads(tf.read_text());j=json.loads(jf.read_text());bays={b['n']:b for b in p['x_relay_bays']};obs=[]
 for c0 in p['children']:
  c=dict(c0)
  if c['n']=='vm_g6_b6_in':c['x'],c['y']=16200.,18863.28
  obs.append(dict(name=c['n'],region=c.get('region'),bbox=[c['x'],c['y'],c['x']+c['w'],c['y']+c['h']],kind='existing_core_or_column',M5_OBS='actualchildrectangle footprint; actualLEFOBS/pins stillrequired forroute'))
 for bay,tiles in t['bay_tiles'].items():
  b=bays[bay]
  if b.get('padrow'):continue
  for q in tiles:
   x=b['x']+q['slot']*21.6;y=b['y'];obs.append(dict(name=f'{bay}:slot{q["slot"]}',region=b.get('region'),bbox=[x,y,x+17.28,y+97.2],kind='existing_regional_lane'))
 for station in j['stations']:
  x,y=station['at_um'];obs.append(dict(name=station['name'],region=1,bbox=[x,y,x+17.28,y+97.2],kind='proposed_reserved_joint_relay'))
 # These broad reservations are an explicit conservative *scenario*, not the
 # parent's actual adopted control/ME footprints. Do not claim unreserved areas.
 x0,y0=p['slot']['origin_um'];W,H=p['slot']['size_um'];cy=p['control_trees']['station_y_um'];virtual=[dict(name='old_PC_LC_control_ribbon_scenario',bbox=[x0,cy-4.32,x0+W,y0+1080],kind='unassigned_virtual_reservation')]
 for i,pin in enumerate(p['me_tree']['slot_me_pins']):
  x,y=pin['x'],pin['y'];virtual.append(dict(name=f'ME_centroid_{i}_broad_scenario',bbox=[x-43.2,y-43.2,x+43.2,y+43.2],kind='unassigned_virtual_reservation'))
 allobs=obs+virtual;records=[];detailed=[]
 for region in range(8):
  ox,oy=p['slot']['region_origins'][str(region)];rw,rh=p['slot']['region_um'][region%4];TW,TH,G=17.28,97.2,2.16
  xs=ox+np.arange(1,math.floor((rw-TW-G)/G)+1)*G;ys=oy+np.arange(1,math.floor((rh-TH-G)/G)+1)*G;allowed=np.ones((len(ys),len(xs)),dtype=bool);touch=[]
  for box in allobs:
   ax,ay,bx,by=box['bbox']
   ix=np.where((xs+TW>ax-G+1e-7)&(xs<bx+G-1e-7))[0];iy=np.where((ys+TH>ay-G+1e-7)&(ys<by+G-1e-7))[0]
   if len(ix)and len(iy):allowed[np.ix_(iy,ix)]=False;touch.append(box['name'])
  valid=np.argwhere(allowed);packed=allowed.copy();selected=[]
  # Deterministic lower-left greedy packing is a feasible subset, not optimum.
  for iy,ix in valid:
   if not packed[iy,ix]:continue
   x,y=xs[ix],ys[iy];selected.append(dict(at_um=[round(float(x),4),round(float(y),4)],outline_um=[TW,TH]))
   xx=np.where((xs+TW>x-G+1e-7)&(xs<x+TW+G-1e-7))[0];yy=np.where((ys+TH>y-G+1e-7)&(ys<y+TH+G-1e-7))[0];packed[np.ix_(yy,xx)]=False
  core=sum(o['kind']=='existing_core_or_column'and o['region']==region for o in obs);lane=sum(o['kind']=='existing_regional_lane'and o['region']==region for o in obs);new=sum(o['kind']=='proposed_reserved_joint_relay'and o['region']==region for o in obs)
  records.append(dict(region=region,origin_um=[ox,oy],outline_um=[rw,rh],existing_core_children=core,existing_lane_children=lane,proposed_reserved_joint_relays=new,
    legal_candidate_lattice_origins=len(valid),greedy_nonoverlap_candidate_P2_footprints=len(selected),greedy_candidate_state_bits=len(selected)*960,virtual_reservation_scenario=True))
  detailed.append(dict(region=region,selected_greedy_candidate_footprints=selected,all_legal_lattice_origins=[[round(float(xs[ix]),4),round(float(ys[iy]),4)]for iy,ix in valid],obstacle_names=touch))
 detail=A/'vm_band_regional_pockets_codex.details.json.gz'
 with gzip.open(detail,'wt')as f:json.dump(dict(regions=detailed,all_obstacles=allobs),f,separators=(',',':'))
 out=dict(schema='opentallas.qwen.vm-regional-export-pocket-census.v1',qualification=False,assigned=False,regional_transport_contract_adopted=False,
  status='CANDIDATE_GEOMETRY_SCENARIO_OWNER_RESERVATIONS_PENDING',source_inputs={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in (lf,tf,jf)},
  adopted_core_override=dict(name='vm_g6_b6_in',absolute_at_um=[16200,18863.28],authority='regionpilot vm_rg6.json d612de244; native19/fullrepack unadopted'),
  full_preserved_core_children=576,full_preserved_region_lane_children=sum(r['existing_lane_children']for r in records),proposed_reserved_joint_relays=2,
  footprint_um=[17.28,97.2],lattice_um=2.16,minimum_channel_um=2.16,regions=records,total_greedy_candidate_footprints=sum(r['greedy_nonoverlap_candidate_P2_footprints']for r in records),
  detail=dict(path=str(detail.relative_to(ROOT)),sha256=hashlib.sha256(detail.read_bytes()).hexdigest()),
  reservations=dict(owner='parent qwen_vm',adopted_actual_reservations='PENDING',scenario_boxes=virtual,scope='Broad26MEcentroid boxes plus entire oldlowerrowcontrolribbon. These are assumedexclusions, NOT a complete actualparent controlplacement receipt.'),
  transport_requirements=['No rawpocketcount becomes assignedslotwithoutowner regionaltransportcontract andactualreservationaudit.','Intermediate actualpin paths≤min500,pairreach; source/ME/loadstep/tag domains andphaseepoch aligned understalls.','RegionM9 abstracts andallrealmacroOBS need actualboundaryport/access/recap beforeVM-owned crossregionrootexportroute.','Bind everyplacedclockphi-R ownentry, localPGM7/actualdieM8M9, fullcombinedcut/SSwire/hold.','Thisgeometryonlyscenario doesnotclose perroot23/39footprintlowerbound into a realpathnetwork.'])
 (A/'vm_band_regional_pockets_codex.json').write_text(json.dumps(out,indent=1)+'\n');print(out['total_greedy_candidate_footprints'],records)
if __name__=='__main__':main()
