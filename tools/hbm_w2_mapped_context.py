"""Mapping-driven complete W2 home worksheet. Does not launch tools or admit P&R."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/hbm_W2_mapped_context_20261003'
def inputs():
 out={}
 for p in json.loads((BASE/'input_pins.json').read_text()):
  raw=(BASE/p['archive']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=p['sha256']:raise ValueError('input pin '+p['archive'])
  out[p['archive']]=json.loads(raw)
 return out
def worksheet(mapping=None):
 x=inputs();m=x['full_controller_model.json'];g=x['qwen_floorplan_r11.json'];facts=x['SS_cell_prices.json']['facts']
 ff=facts['DFFASRHQNx1_ASAP7_75t_R']['SS'];buf=facts['BUFx4_ASAP7_75t_R']['SS'];inv=facts['INVx1_ASAP7_75t_R']['SS']
 if mapping is not None:
  if mapping.get('stage')!='synthesis':raise ValueError('preCTS synthesis mapping only; no duplicate CTS debit')
  if mapping.get('source_sha256')!=m['source_sha256'] or mapping.get('parameters')!=m['parameters'] or mapping.get('corner')!='SS':raise ValueError('full exact SS source binding')
  rows=mapping.get('CW_rows',[])
  if len(rows)!=219 or sorted(r['index'] for r in rows)!=list(range(219)) or any(len(r['cells'])!=72 for r in rows):raise ValueError('219x72 CW census')
  cells=[c for r in rows for c in r['cells']]
  if len(set(cells))!=15768 or any(not isinstance(c,str) or not c for c in cells):raise ValueError('duplicate/missing physical CW cell')
  body=mapping.get('standard_cell_area_um2')
  if not isinstance(body,(int,float)) or not math.isfinite(body) or body<=0:raise ValueError('mapped area')
  if not mapping.get('mapped_netlist_sha256') or not mapping.get('SS_report_sha256'):raise ValueError('raw mapped provenance')
  basis='source-bound external SS mapping input; independent raw-netlist verification remains Hubble-owned'
 else:
  body=m['area']['full_source_selector_exposed_budget_mm2_per_PC']*1e6;basis='e859 full219 analytical reserve, not a mapped measurement'
 regions=[r for r in g['regions'] if r['kind']=='service'];assert len(regions)==2
 width=math.ceil((regions[0]['w']/64)/.054)*.054
 pg=g['reserves']['PDN_charged_site_fraction'];util=.5
 pb=m['ports']['book'];ib=m['ports']['input_bits']-2;ob=m['ports']['output_bits']
 # Concrete SS master choices for a qualification context, not installed callers.
 # Input BUF driver and output registered terminator, including QN inverter.
 term_area=ib*buf['area_um2']+ob*(ff['area_um2']+inv['area_um2'])
 tree=lambda n:sum(math.ceil(n/8**i) for i in range(1,1+math.ceil(math.log(max(n,2),8))))
 clock_sinks=15768+ob
 tree_area=2*tree(clock_sinks)*buf['area_um2']
 tree_added=tree_area if mapping is not None else 0
 need=(body+term_area+tree_added)/(util*(1-pg))
 height=math.ceil(need/width/.27)*.27
 collisions=[]
 for region in regions:
  south=region['name']=='svc_south';y=region['y'] if south else region['y']+region['h']-height
  b=[region['x'],y,region['x']+region['w'],y+height]
  for n in g['regions']:
   if n['kind'] in ['service','die']:continue
   if b[0]<n['x']+n['w'] and b[2]>n['x'] and b[1]<n['y']+n['h'] and b[3]>n['y']:collisions.append({'band':region['name'],'neighbor':n['name']})
 contracts={n:dict(direction=p['direction'],bits=p['bits'],driver_cell='BUFx4_ASAP7_75t_R' if p['direction']=='input' else None,capture_cell='DFFASRHQNx1_ASAP7_75t_R' if p['direction']=='output' else None,per_bit_load_fF=ff['pins']['D']['cap_fF'] if p['direction']=='output' else None,actual_source_owner=None,actual_arrival_slew_and_wire_RC=None) for n,p in pb.items() if n not in ['clk','rst_n']}
 return dict(source_model='e859a4d278786fb4847fc668209e7a8ca5093aa3',source_sha256=m['source_sha256'],basis=basis,mapped_input_present=mapping is not None,independent_mapping_verified=False,CW_required=219,protected_FF_required=15768,ports=contracts,
  local_context=dict(width_um=width,height_um=height,area_mm2=width*height/1e6,placement_fraction=util,PG_site_exclusion_fraction=pg,PG_profile=g['reserves']['PDN_profile'],PG_policy_not_extracted_mask=True,body_um2=body,port_termination_area_um2=term_area,clock_reset_buffer_area_reserve_um2=tree_area,clock_reset_additional_debit_um2=tree_added,clock_reset_floor_already_in_e859=mapping is None,buffer_fanout=8,clock_leaf_load_fF=8*ff['pins']['CLK']['cap_fF'],reset_leaf_load_upper_fF=8*max(ff['pins']['SETN']['cap_fF'],ff['pins']['RESETN']['cap_fF']),buffer_SS_max_load_fF=buf['pins']['Y']['max_cap_fF'],clock_total_pin_load_fF=clock_sinks*ff['pins']['CLK']['cap_fF'],controller_reset_pin_load_fF_range=[min(p['reset_SS_fF'] for p in m['area']['reset_by_PC'].values()),max(p['reset_SS_fF'] for p in m['area']['reset_by_PC'].values())],driver_load_choices='qualification-context cells; not instantiated parent producer proof',loaded_cell_arc_skew_and_voltage_drop=None),
  global_screen=dict(PCs_per_die=128,requested_controllers=1280,die_local_namespace=128,new_band_width_um=width*64,body_mm2_per_128=body*128/1e6,footprint_mm2_per_128=need*128/1e6,current_r11_service_bands_mm2=sum(r['w']*r['h'] for r in regions)/1e6,old_band_height_um=regions[0]['h'],additional_band_depth_um=max(0,height-regions[0]['h']),neighbor_collisions_if_stretched=collisions,service_envelope_mm2=x['service_inventory.json']['models']['Qwen']['area']['service_envelope_mm2'],service_envelope_is_NOT_free=True,matched_old_W2_replacement_credit=None,RF_scratch_L2_body_added_again=0),
  routing=dict(complete_boundary_bits=m['ports']['boundary_signal_bits'],prospective_vertical_M3_M5_half_signal_tracks=math.floor(width*(1/.036+1/.048)/2),actual_PG_OBS_pin_escape_capacity=None),
  physical_admitted=False,new_jobs=0,clock=dict(period_ps=2500/3,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),required=['Hubble exact SS mapping and unique15768 CW cell census before final dimension selection','Claude actual slot/home/neighbor relocation and matched old W2 debit','Installed client/backend driver/capture source identities and measured SS/FF arcs plus RC','Actual PG/CTS/reset/route exclusions and power/IR; current reserves are constructive planning only'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mapping',type=Path);a=p.parse_args()
 print(json.dumps(worksheet(json.loads(a.mapping.read_text()) if a.mapping else None),indent=2,sort_keys=True))
