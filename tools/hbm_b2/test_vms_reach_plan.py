"""The proposed physical kernel must meet its bound at every die corner."""
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import vms_reach_plan as P

def test_kernel_has_the_claimed_whole_outline_bound():
    D=SimpleNamespace(die=(0,0,270,403.92),extra=dict(core=(4.32,4.32,265.68,399.6)),cells={})
    box,_=P.kernel(D,395)
    for x in [box[0],box[2]]:
        for y in [box[1],box[3]]:
            assert max(abs(x-a)+abs(y-b) for a in [0,270] for b in [0,403.92])<=395+1e-7

def test_unreachable_outline_is_rejected_before_placement():
    D=SimpleNamespace(die=(0,0,1000,1000),extra=dict(core=(4.32,4.32,995.68,995.68)),cells={})
    try:P.kernel(D,395)
    except ValueError as e:assert 'structural' in str(e)
    else:raise AssertionError('impossible kernel accepted')
