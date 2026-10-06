"""Negative controls for the native route's conditional SS/FF decision."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from hbm_item9_native_loaded_route import corner_verdict


LOG = 'OT_CORNER ss\nOT_WS 3.5e-12\nOT_WS_R2R 3.5\nOT_VIOL_D_PINS 0\n'


def test_positive_internal_evidence_never_qualifies_parent():
    result = corner_verdict(LOG, 'ss', 0)
    assert result['conditional_internal_timing_pass']
    assert result['worst_slack_ps'] == pytest.approx(3.5)
    assert not result['parent_qualified']
    assert not result['full_endpoint_signoff']


@pytest.mark.parametrize('content,corner,exitcode', [
    (LOG.replace('3.5e-12', '-1e-15'), 'ss', 0),
    (LOG.replace('OT_WS_R2R 3.5', 'OT_WS_R2R -0.001'), 'ss', 0),
    (LOG.replace('OT_VIOL_D_PINS 0', 'OT_VIOL_D_PINS 1'), 'ss', 0),
    (LOG.replace('OT_WS 3.5e-12\n', ''), 'ss', 0),
    (LOG.replace('3.5e-12', 'INF'), 'ss', 0),
    (LOG.replace('3.5e-12', 'NaN'), 'ss', 0),
    (LOG.replace('3.5e-12', 'invalid'), 'ss', 0),
    (LOG.replace('OT_WS_R2R 3.5', 'OT_WS_R2R INF'), 'ss', 0),
    (LOG + 'OT_WS 3.5e-12\n', 'ss', 0),
    (LOG.replace('OT_VIOL_D_PINS 0', 'OT_VIOL_D_PINS -1'), 'ss', 0),
    (LOG.replace('OT_VIOL_D_PINS 0', 'OT_VIOL_D_PINS 0.5'), 'ss', 0),
    (LOG, 'ff', 0),
    (LOG, 'ss', 1),
    (LOG + '[ERROR STA-0001] library missing\n', 'ss', 0),
])
def test_reject_negative_missing_or_invalid_evidence(content, corner, exitcode):
    assert not corner_verdict(content, corner, exitcode)['conditional_internal_timing_pass']
