import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('p',Path(__file__).parents[1]/'tools/v41_pv_bank_lifetime.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
def test_three_banks_overwrite_live_operands():
    x=p.analyze(3); assert x['violation_count']>0 and x['min_margin']==-8
    assert p.replay_corruption(3)['errors']>0

def test_four_banks_are_minimum_for_eight_cycle_blocks():
    assert all(p.analyze(n)['violation_count']>0 for n in (1,2,3))
    x=p.analyze(4);assert x['violation_count']==0 and x['min_margin']==0
    assert p.replay_corruption(4)['errors']==0
    assert x['storage_bytes']-p.analyze(3)['storage_bytes']==65536
