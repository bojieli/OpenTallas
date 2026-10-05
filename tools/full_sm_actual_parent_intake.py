#!/usr/bin/env python3
"""Verify actual ODB/mapped-source intake and price a bounded GPU parent outline.
No source rewriting, compilation, OpenROAD, qualification or build admission.
"""
import argparse,gzip,hashlib,json,math,re,resource,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/full_sm_actual_parent_route_20261002'
BASE=ROOT/'results/uarch/dsrom_l20_hierarchical_reservation_20261002'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,a):
 b=(json.dumps(a,indent=2,sort_keys=True)+'\n').encode();p=OUT/name
 if p.exists():assert p.read_bytes()==b, name+' evidence drift'
 else:p.write_bytes(b)
def main():
 resource.setrlimit(resource.RLIMIT_AS,(16*1024**3,16*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU,(600,600))
 ap=argparse.ArgumentParser();ap.add_argument('--geometry-dir',type=Path,required=True);ap.add_argument('--source-dir',type=Path,required=True);a=ap.parse_args()
 model=json.load(open(OUT/'model.json'));bindings=json.load(open(OUT/'mapped_source_binding.json'));capacity=json.load(open(BASE/'actual_grid_usable_capacity.json'))
 result={};outlines={}
 dependency_pins={}
 rf_provider=json.load(open(BASE/'grid_inputs/DS_grid.json'))['macro_master_OBS']['ot_sram_1r1w_128x256_m1_r2c2']
 assert rf_provider['size']==[94824,41040]
 assert {o['layer'] for o in rf_provider['OBS']}=={'M1','M2','M3','M4'}
 for path in ['rtl/gpu/ot_gpu_xstore.sv','rtl/gpu/ot_gpu_fadd.sv','rtl/gpu/ot_gpu_bd_col.sv']:
  data=subprocess.check_output(['git','show','000ba0898f5120a66d5905ccff333ebbbe28394d:'+path],cwd=ROOT);dependency_pins[path]=sha(data)
 for k in ['DS','Qwen']:
  blob=(a.geometry_dir/(k+'_geometry.json.gz')).read_bytes();g=json.loads(gzip.decompress(blob));v=capacity['models'][k];m=model['models'][k];b=bindings[k]
  assert sha(blob)==v['export_sha256']==m['export_sha256']
  assert g['ODB_sha256']==v['ODB_sha256']==b['ODB_sha256']==m['ODB_sha256']
  assert g['dbu_per_um']==1000 and not g['routing_obstructions'] and not g['placement_blockages']
  assert not g['ODB_mutations'] and not g['physical_flow_commands_run']
  grid_path=BASE/'grid_inputs'/(k+'_grid.json');grid=json.load(open(grid_path));assert sha(grid_path.read_bytes())==v['grid_sha256']
  src=gzip.decompress((a.source_dir/(k+'_mapped.v.gz')).read_bytes());assert sha(src)==b['mapped_source_sha256'];s=src.decode();del src
  inputs=set()
  for h,l,n in re.findall(r'^  input \[(\d+):(\d+)\] (\S+)\s*;',s,re.M):
   n=n.replace('\\','');inputs.update(n+f'[{i}]' for i in range(int(l),int(h)+1))
  inputs.update(n.replace('\\','') for n in re.findall(r'^  input (\S+)\s*;',s,re.M))
  missing=set(b['primary_or_missing_driver_frontier_ids'])-inputs;assert not missing
  ff={f['name'].replace('\\','') for f in g['FF_instances']};assert len(ff)==b['actual_FFs']
  cones=json.load(gzip.open(OUT/b['parent_cone_frontier_ledger'],'rt'))
  reached={r[3:] for x in cones.values() for r in x['actual_driver_frontier'] if r.startswith('FF:')};assert reached<=ff and len(reached)==b['actual_FF_driver_frontier_count']
  pins=json.load(gzip.open(OUT/b['source_macro_pin_binding'],'rt'))
  assert len(pins)==m['all_connected_macro_signal_endpoint_count']
  assert len({p['source_resolved_net'] for p in pins})==m['all_connected_macro_signal_net_count']
  assert all(p['access_DBU'] is not None for p in pins)
  # Every boundary-driver frontier is a real top input, never an ODB netNN.
  # Tied wires retain all endpoint/fanout charges in the conservative screen.
  ties=[]
  for match in re.finditer(r'^  (TIE(?:HI|LO)\S*) (\S+)\s+\(\n(.*?)^  \);',s,re.M|re.S):
   master,name,body=match.groups();n=re.search(r'\.[HL]\((.*?)\)',body)[1].strip().replace('\\','')
   ties.append(dict(master=master,instance=name,net=n,macro_pin_loads=sum(p['source_resolved_net']==n for p in pins),physical_fanout_remains_charged=True))
  assert len(ties)==2
  # Exact OBS layers rather than treating the OBS-record count as layer count.
  obs={name:sorted({o['layer'] for o in x['OBS']}) for name,x in grid['macro_master_OBS'].items()}
  assert all(set(layers)&{'M1','M2','M3','M4'}=={'M1','M2','M3','M4'} for layers in obs.values())
  for cut in v['native_cut_capacity']:
   for r in cut['cut_records']:
    assert r['free_tracks']+r['all_OBS_halo_PDN_via_blocked_tracks']==cut['unique_track_count']
    assert r['policy50pct_signal_tracks']==r['free_tracks']//2
  assert math.isclose(v['remaining_ROW_site_area_um2']-v['physical_cell_site_union_debit_um2'],v['usable_post_cut_ROW_site_area_um2'],abs_tol=1e-6)
  assert m['actual_parent_cell_reservation_um2']<=v['parent50pct_cell_capacity_um2']
  directional_cuts={}
  for layer in v['native_cut_capacity']:
   for r in layer['cut_records']:
    demand=next(t for t in m['native_parent_route_cut_screens'][layer['layer']] if t['cut_DBU']==r['cut_DBU'])['macro_to_macro_unique_net_lower_demand']
    row=directional_cuts.setdefault((layer['direction'],r['cut_DBU']),[0,demand]);assert row[1]==demand;row[0]+=r['policy50pct_signal_tracks']
  macro_cut_failures=[dict(direction=d,cut_DBU=c,required_unique_macro_nets=n,available_signal_tracks=cap) for (d,c),(cap,n) in directional_cuts.items() if n>cap]
  W,H=[x/1000 for x in g['die'][2:]];halo=4.0
  boundary_payload=2048+m['actual_params']['NC']*32
  # Price the actual x-write and result buses plus an explicit64wire control
  # reservation; this is a necessary boundary screen, not a service guarantee.
  boundary_reservation=boundary_payload+64
  gap=math.ceil((2*boundary_reservation/(1000/64+1000/80)+4.32)/2.16)*2.16
  # Existing shallow 1R1W RF providers, two operand copies; no free read ports.
  rw,rh=94.824+2*halo,41.04+2*halo;sw,sh=174.744+2*halo,70.47+2*halo
  rf_w,rf_h=8*rw,16*rh;scratch_w,scratch_h=2*sw,sh
  nm=m['nonmatrix_reservation'];logic=(nm['SIMD_cell_proxy_um2']+nm['RF_mux_cell_proxy_um2']+16*4*2*32*5*.2)/.5
  # Dense-array SRAM rectangles already include 4um halos; logic receives a
  # separate 50%-utilization rectangle, and a source-sized boundary channel stays unoccupied.
  service_w=math.ceil(max(rf_w,scratch_w)/2.16)*2.16
  logic_h=math.ceil(logic/service_w/2.16)*2.16
  service_h=rf_h+scratch_h+logic_h+2*gap
  height=math.ceil(max(H,service_h)/2.16)*2.16;width=math.ceil((W+gap+service_w)/2.16)*2.16
  macro_boxes=[]
  for i in range(128):
   x=W+gap+(i%8)*rw;y=(i//8)*rh
   macro_boxes.append(dict(name='proposed_RF_readcopy_page_'+str(i),master='ot_sram_1r1w_128x256_m1_r2c2',abstract_provider_grid='DS_grid.json',abstract_provider_scope='Retained same-process DS shallow SRAM; not present in retained Qwen matrix parent; no timing transfer',halo_bbox_um=[x,y,x+rw,y+rh],provider_bound=False))
  for i in range(2):
   x=W+gap+i*sw;y=rf_h+gap
   macro_boxes.append(dict(name='proposed_scratch_'+str(i),master=next(n for n in grid['macro_master_OBS'] if '1024x256' in n),halo_bbox_um=[x,y,x+sw,y+sh],provider_bound=False))
  array=[8*width,4*height];reticle=sorted([26000.,33000.]);assert all(x<=y for x,y in zip(sorted(array),reticle))
  outlines[k]=dict(element_outline_um=[width,height],element_gross_mm2=width*height/1e6,SM_replicas=32,array_columns=8,array_rows=4,array_outline_um=array,array_gross_mm2=math.prod(array)/1e6,reticle_um=[26000,33000],reticle_area_screen=True,reticle_source='e72abea5ae169d3167dddc89543013f0e6bb3a7a:tools/uarch_model.py HBM_SHORE.reticle_mm; parent54d46eff8 corroborates',retained_macro_body_um=[0,0,W,H],retained_parent_cells_use_actual_postcut_ROW_sites=True,additional_service_halo_rectangles=macro_boxes,service_logic_50pct_rectangle_um=[W+gap,rf_h+scratch_h+2*gap,W+gap+service_w,service_h],dedicated_service_channel_um=[W,0,W+gap,height],channel_M7_M9_50pct_track_budget=math.floor(gap*1000/64/2)+math.floor(gap*1000/80/2),channel_payload_source_lower_bound_tracks=boundary_payload,channel_control_reserved_tracks=64,channel_complete_provider_demand_bound=False,existing_native_OBS_capacity_file='actual_geometry_capacity.json',RF_read_payload_bits_pc=8192,RF_write_logical_bits_pc=4096,RF_mirrored_physical_write_bits_pc=8192,RF_visible_write_ack_and_bank_arbitration_provider_bound=False,macro_pin_escape_qualified=False,actual_parent_placed=False,current_shared_RNE_integrated=False,added_transport_cycles=None,token_admission=False,verdict='AREA_AND_RETICLE_FIT_ONLY: source-native parent placement and finite service route schedule still required; not an admissible routed layout',four_target_applicability={'Qwen_HBM':k=='Qwen','DS_HBM':k=='DS','Qwen_ROM':False,'DS_ROM':False},ROM_transfer=False)
  result[k]=dict(checks_pass=True,ODB_sha256=g['ODB_sha256'],geometry_export_sha256=sha(blob),grid_sha256=v['grid_sha256'],mapped_source_sha256=b['mapped_source_sha256'],declared_primary_input_bits=len(inputs),all_input_driver_frontiers_bound=True,missing_driver_ids=[],FF_count=len(ff),FF_driver_frontier_count=len(reached),macro_count=len(g['macro_instances']),macro_signal_pin_count=len(pins),macro_signal_unique_source_nets=len(cones),tie_source_proof=ties,OBS_layers_by_master=obs,sampled_macro_only_multiplane_cut_failures=macro_cut_failures,sampled_macro_only_cut_count=len(directional_cuts),sampled_cut_screen_is_not_global_routability=True,full_OBS_halo_PDN_via_track_accounting_checked=True,routing_obstructions_count=0,placement_blockages_count=0,cell_capacity_um2=v['parent50pct_cell_capacity_um2'],priced_parent_cell_um2=m['actual_parent_cell_reservation_um2'],centralized_layout_FAIL_preserved=True,standalone_column_qualification_transferred=False)
  del g,cones,pins,s
 write('actual_geometry_capacity.json',capacity)
 write('priced_full_SM_area_outline.json',dict(schema='opentallas.fullSM.native-parent-area-outline.v1',models=outlines,full_SM_build_GO=False,source_dependency_pins=dependency_pins,clock_policy=dict(streaming_GHz=1.2,serial_chain_GHz=.9,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,full_parent_SSFF_not_measured=True),original_failures_unchanged=True,new_OpenROAD_invocations=0))
 write('static_checks.json',dict(schema='opentallas.fullSM.native-parent-static-intake.v1',models=result,generator_sha256=sha(Path(__file__).read_bytes()),full_SM_build_GO=False))
 print(json.dumps({k:dict(checks_pass=v['checks_pass'],area_outline_mm2=outlines[k]['element_gross_mm2'],array_mm2=outlines[k]['array_gross_mm2'],full_SM_build_GO=False) for k,v in result.items()}))
if __name__=='__main__':main()
