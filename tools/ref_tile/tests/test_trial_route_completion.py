"""A zero-overflow intermediate table cannot qualify a failed OpenROAD trial route."""
from pathlib import Path
import sys
import tempfile
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as P


def report(rc, overflow=0, table=True):
    out = f"GATE_GRT_RC={rc}\nGATE_GRT_S=19\n"
    if table:
        out += f"GATE_GRT_LAYER M4 100 20 20.0% 0 / 0 / {overflow}\n"
        out += f"GATE_GRT_LAYER Total 100 20 20.0% 0 / 0 / {overflow}\n"
    g = P.Gate()
    with tempfile.TemporaryDirectory() as t:
        P.gate_layout(g, Path(t), dict(kind='tile', name='fixture'), out)
    return g


@pytest.mark.parametrize('rc', ['2', '139', 'signal'])
def test_failed_route_refuses_even_with_zero_overflow_table(rc):
    g = report(rc)
    assert g.trial_route['rc'] == rc and g.trial_route['overflow'] == 0
    assert any(x['severity'] == 'FAIL' and x['check'] == 'trial_route' for x in g.items)


def test_successful_zero_overflow_route_qualifies():
    g = report('0')
    assert any(x['severity'] == 'INFO' and x['check'] == 'trial_route' for x in g.items)
    assert not any(x['severity'] == 'FAIL' and x['check'] == 'trial_route' for x in g.items)


def test_success_still_requires_a_table_and_zero_overflow():
    for g in (report('0', table=False), report('0', overflow=7)):
        assert any(x['severity'] == 'FAIL' and x['check'] == 'trial_route' for x in g.items)
