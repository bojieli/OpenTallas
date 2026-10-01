import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w13_index_lane_allocation as M

def manifest():
 import subprocess,json
 return json.loads(subprocess.check_output(['git','show','0dac17bf9:'+M.PATH]))['executed_producer']['executed_ordinary_events']

def test_source_lane_versions_and_finite_registers():
 d=M.build()
 assert {k:v['peak_conservative_registers_per_lane'] for k,v in d['kernels'].items()}=={'classify':2,'finite_blocks':22,'exceptional_blocks':7}
 for k,v in d['kernels'].items():
  assert v['issues']==[] and v['resident_source_warps']<=32
  for e in v['events']:
   for o in e['operand_register_bindings']:assert 0<=o['physical_register']<32
   for r in e['result_register_bindings']:assert r['physical_write_copies']==[0,1]
   assert e['RF_read_tick'] is None and e['shared_service_tick'] is None
 assert d['full64tile_actual_operand_manifest'] is None and not d['physical_admission']

def test_shuffle_wrong_source_lane_rejected():
 events=copy.deepcopy(manifest()['classify']);e=next(x for x in events if x['opcode']=='SHFL');o=e['operand_register_bindings'][0]
 o['source_lane']=(o['source_lane']+1)%32
 assert any(x.startswith('stale_lane_version:') for x in M.allocate(events)['issues'])

def test_masked_write_nonowner_and_three_read_rejected():
 events=copy.deepcopy(manifest()['classify']);e=events[2];e['active_lanes'][0]['lanes'].remove(0)
 assert 'masked_write_outside_active_lane' in M.allocate(events)['issues']
 events=copy.deepcopy(manifest()['classify']);e=next(x for x in events if x['operand_register_bindings'])
 o=copy.deepcopy(e['operand_register_bindings'][0]);e['operand_register_bindings'] += [o,o]
 assert 'lane_2R1W_aperture' in M.allocate(events)['issues']
