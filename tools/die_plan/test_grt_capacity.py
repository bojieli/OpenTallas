"""A wrapped routing-capacity table cannot be reported as zero-overflow PASS."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g2

CLEAN='''
[INFO GRT-0096] Final congestion report:
M6 10000 4000 40.00% 0 / 0 / 0
Total 10000 4000 40.00% 0 / 0 / 0
OT_DONE
'''


def test_real_grt_warning_underflow_invalidates_apparent_zero():
    log='[WARNING GRT-0114] Underflow in reduce: cap, reducedCap: 0, 65480\n'+CLEAN
    r=g2.parse_grt(log)
    assert r['reported_total_overflow']==0 and r['tool_done']
    assert r['total_overflow'] is None and not r['capacity_valid'] and not r['done']
    assert 'GRT-0114' in r['errors'] and not g2.probe_passes(r)
    # Removing the actual underflow warning is an explicit mutant control.
    good=g2.parse_grt(CLEAN)
    assert good['total_overflow']==0 and good['capacity_valid'] and g2.probe_passes(good)


def test_impossible_reduction_rejected_without_diagnostic_id():
    r=g2.parse_grt('cap, reducedCap: 0, 65446\n'+CLEAN)
    assert not r['capacity_valid'] and 'GRT-CAPACITY-UNDERFLOW' in r['errors']


def test_legitimate_capacity_reduction_and_large_net_number_are_not_rejected():
    r=g2.parse_grt('[INFO GRT] cap, reducedCap: 80, 48\nnet65480 route\n'+CLEAN)
    assert r['capacity_valid'] and g2.probe_passes(r)
