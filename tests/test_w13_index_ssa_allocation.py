import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_ssa_allocation import build

def test_selected_ssa_register_budget_and_interference():
 d=build();a=d['allocation'];assert a['issues']==[]
 assert a['allocated_version_registers']==10 and a['total_per_lane_registers']==18<=32
 colors={tuple(g['group']):g['register'] for g in a['allocation_group_colors']}
 for g in a['allocation_group_colors']:
  assert all(colors[tuple(other)]!=g['register'] for other in g['interferes_with'])
 assert not d['physical_admission'] and not d['whole64_SSA_expanded']

def test_uniform_operand_numbers_no_free_lane_mux():
 a=build()['allocation']
 for e in a['events']:
  groups={}
  for o in e['operand_register_bindings']:
   groups.setdefault(o['operand_index'],set()).add(o['physical_register'])
   assert 0<=o['physical_register']<24
  assert all(len(regs)==1 for regs in groups.values())
  for r in e['result_register_bindings']:
   assert 0<=r['physical_register']<24 and r['write_copies']==[0,1]
  assert e['RF_read_tick'] is None and e['RF_writeback_tick'] is None
 assert a['actual_timing'] is None
