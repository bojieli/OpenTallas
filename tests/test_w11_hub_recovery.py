"""Historical calibration must reject false verdicts and invalid issue timing."""
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w11_hub_recovery_check as C


def test_reproducible_calibration():
    assert C.check() == json.loads((C.BASE / 'calibration.json').read_text())


@pytest.mark.parametrize('mutation', ['verdict', 'cycles', 'order', 'exactness'])
def test_reject_invalid_trace_or_verdict(mutation):
    record = C.read('results/rtl/w11_controller_recovery_20261001/u2517.json')
    trace = C.read('results/rtl/w11_controller_recovery_20261001/u2517.issues.json')
    if mutation == 'verdict':
        record['status'] = 'pass'
    elif mutation == 'cycles':
        record['single_step']['cycles'] += 1
    elif mutation == 'exactness':
        record['single_step']['logit_mismatches'] = 1
    else:
        trace['runs'][0]['issues'][1][0] = -1
    with pytest.raises(AssertionError):
        C.attribution(record, trace)
