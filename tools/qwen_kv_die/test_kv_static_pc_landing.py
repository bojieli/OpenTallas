"""KV-INT-R2 11-26: plan latency.pc_landing_extra drives kv_static_programme landing_uncertainty (default 1 unchanged)."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kv_static_programme as P  # noqa: E402


def _plan(lat):
    d = tempfile.mkdtemp()
    f = Path(d) / 'plan.json'
    f.write_text(json.dumps(dict(latency=lat)))
    return str(f)


def test_default_zero():
    assert P.plan_pc_landing_extra(None) == 0
    assert P.plan_pc_landing_extra(_plan({'lanes': {}})) == 0


def test_declared_extra():
    assert P.plan_pc_landing_extra(_plan({'pc_landing_extra': 4})) == 4


def test_bad_extra_refused():
    for bad in (-1, 65, 1.5, True, '4'):
        try:
            P.plan_pc_landing_extra(_plan({'pc_landing_extra': bad}))
        except ValueError:
            continue
        raise AssertionError(bad)
