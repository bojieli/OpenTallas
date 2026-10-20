import json,hashlib
from pathlib import Path
p=Path('.');read=lambda n:json.loads((p/'inputs'/n).read_text())
t=read('compressed_topology.json');by={x['id']:x for x in t};roles=read('native_tables.json')['roles'];ledger=[];branches=[]
def add(driver,role,endpoints,**extra):
 ledger.append(dict(driver=driver,role=role,transparent_endpoint_count=len(endpoints),endpoints=endpoints,actual_wire_cap_fF=None,scope='SOURCE_MODEL_NOT_MAPPED',**extra))
for x in t:
 n=f"n{x['id']}";groups=[x['sink_indices'][i:i+24] for i in range(0,len(x['sink_indices']),24)]
 assert len(groups)==x['leaf_pairs']
 for k in range(1+len(groups)):
  b=f'{n}/p{k}';reset_loads=[f"n{i}/p0/ff1/RESETN" for i in x['children']]+[f'{n}/p{j+1}/ff1/RESETN' for j in range(len(groups))] if k==0 else [f'boundary/{i}/RESETN' for i in groups[k-1]]
  for driver in ['ff1/QN','release_inv/Y']:add(b+'/'+driver,'reset_release1',[b+'/ff2/RESETN'])
  for driver in ['ff2/QN','output_inv/Y']:add(b+'/'+driver,'reset_output',reset_loads,external_boundary_native_caps_known=(k==0))
  add(b+'/clock_inv/Y','genuine_native_clock',[b+'/ff1/CLK'])
 add(n+'/tie/H','constant',[f'{n}/p{k}/{ff}/{pin}' for k in range(1+len(groups)) for ff in ['ff1','ff2'] for pin in ['D','SETN']])
 # Explicit primitive clock pins, with real clock inverter input retained.
 direct=[f'n{i}/clock/A' for i in x['children']]+[f'{n}/p{k}/{pin}' for k in range(1+len(groups)) for pin in ['ff2/CLK','clock_inv/A']]
 stack=[x];desc=[]
 while stack:
  a=stack.pop();desc.extend(f"n{a['id']}/p{k}/{ff}/CLK" for k in range(1+a['leaf_pairs']) for ff in ['ff1','ff2']);stack.extend(by[i] for i in a['children'])
 add(n+'/clock/Y','genuine_native_clock',desc,direct_native_endpoints=direct,direct_native_count=len(direct),clock_transparency='uncapped native FF clock leaves; no name exclusion')
 for i in x['children']:
  child=by[i];length=child['path_um']+3
  for corner in ['TT','FF']:
   cpin=float(roles[corner+':DFFASRHQNx1']['pins']['RESETN']['capacitance'][0])
   for layer,r,c in [('M6',.0118796,.187426),('M7',.0125096,.162979)]:
    branches.append(dict(parent=x['id'],child=i,corner=corner,layer=layer,recorded_path_um=child['path_um'],contact_allowance_um=3,native_child_FF1_cap_fF=cpin,wire_cap_fF=c*length,independent_branch_elmore_ps=r*length*(c*length/2+cpin),actual_branched_RC_graph=None))
assert len(ledger)==18311
nonclock=[d for d in ledger if d['role']!='genuine_native_clock']
assert max(d['transparent_endpoint_count'] for d in nonclock)<=32
(p/'all_native_output_source_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
new_ledger=ledger;ledger=[]
for x in t:
 n=f"n{x['id']}";groups=[x['sink_indices'][i:i+24] for i in range(0,len(x['sink_indices']),24)]
 for k in range(1+len(groups)):
  b=f'{n}/p{k}';loads=[f"n{i}/p0/{ff}/RESETN" for i in x['children'] for ff in ['ff1','ff2']]+[f'{n}/p{j+1}/{ff}/RESETN' for j in range(len(groups)) for ff in ['ff1','ff2']] if k==0 else [f'boundary/{i}/RESETN' for i in groups[k-1]]
  for driver in ['ff1/QN','inv1/Y']:add(b+'/'+driver,'data_to_D',[b+'/ff2/D'])
  for driver in ['ff2/QN','inv2/Y']:add(b+'/'+driver,'reset_output',loads)
 add(n+'/tie/H','constant',[f'{n}/p{k}/{ff}/{pin}' for k in range(1+len(groups)) for ff,pin in [('ff1','D'),('ff1','SETN'),('ff2','SETN')]])
 clock=next(d for d in new_ledger if d['driver']==n+'/clock/Y')
 add(n+'/clock/Y','genuine_native_clock',clock['endpoints'],direct_native_count=x['clock_direct_loads'])
assert len(ledger)==15554
(p/'old_all_native_output_source_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
old_summary=dict(rows=len(ledger),transparent_INV_rows=5514,max_nonclock_transparent_loads=max(d['transparent_endpoint_count'] for d in ledger if d['role']!='genuine_native_clock'),scope='STATIC_SOURCE_EQUATION_NOT_MAPPED_STRICT_CERTIFICATE')
ledger=new_ledger
(p/'recorded_branch_rc_model.json').write_text(json.dumps(branches,indent=1)+'\n')
receipt=dict(status='FUNCTIONAL_SOURCE_ONLY_APERTURE_REFUSED',native_output_driver_rows=len(ledger),transparent_INV_rows=8271,full_clock_leaf_max=max(d['transparent_endpoint_count'] for d in ledger if d['role']=='genuine_native_clock'),max_nonclock_transparent_loads=max(d['transparent_endpoint_count'] for d in nonclock),cost=read('candidate_cost.json'),operating_envelope=dict(period_ps=1024,duty_fraction=None,root_POR_release_aperture=None,source_PLL_drive_phase=None,unwrapped_clock_ancestry=None,actual_branched_RC_graph=None,shared_segment_and_via_RC=None,contact_polarities_and_waveforms=None,native_load_slew_correlated_domain=None,boundary_810_native_pin_caps=None,compiler_age=None),missing_before_physical_age=['actual branch graph with common segment/via RC and min/max','source duty and native clock inverter rise/fall waveform','TT/FF correlated min/max phase and load/slew inside native table grids','root POR release aperture and 179-depth unwrapped ancestry','810 boundary pin master/caps and row ownership phase'],aperture='Dmax + recovery + 60 <= g <= 1024 + Dmin - removal - 25',physical_qualification=False)
(p/'model_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['cost']},indent=2))
(p/'old_source_ledger_receipt.json').write_text(json.dumps(old_summary,indent=2)+'\n')
