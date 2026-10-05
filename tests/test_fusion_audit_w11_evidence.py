"""Attribution regressions: preserve failed verdicts and distinguish waits from busy time."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import fusion_audit_w11_evidence as E


def record():
    return json.loads(E.RECORD.read_text())


def test_source_pins_and_issue_attribution():
    E.verify(record())


@pytest.mark.parametrize('mutation', ['busy', 'verdict', 'cycles', 'source'])
def test_reject_false_attribution(mutation):
    r = copy.deepcopy(record())
    if mutation == 'busy':
        r['historical_reduced_rtl']['f00']['per_region_su_busy_cycles'] = {
            'attn': r['historical_reduced_rtl']['f00']['su_issue_attributed_intervals_by_region']['attn']}
    elif mutation == 'verdict':
        r['historical_reduced_rtl']['f00']['status'] = 'pass'
    elif mutation == 'cycles':
        r['estimates']['shipped']['fused']['hidden'] = 3681
    else:
        r['git_sources'][0]['sha256'] = '0' * 64
    with pytest.raises(AssertionError):
        E.verify(r)
