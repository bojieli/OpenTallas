"""HOLD-MARGIN-FAMILY 11-17: die.hold_ff_margin_ps / partition type hold_ff_margin_ps are schema keys.  hold_margin_family.py reads
them, but schema.py refused both as unknown keys (plan_gate_pre SCHEMA-UNKNOWN-KEY), so no plan could set them (S81-DIE-R3 D8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_margin_family as F  # noqa: E402
import schema as S  # noqa: E402

DIE = {"name": "s81", "outline_um": [100.0, 100.0], "period_ps": 833, "reach_um": 405}


def _die_errs(d):
    errs = []
    S._check(d, S.SCHEMA["properties"]["die"], "$.die", errs)
    return errs


def test_die_key_accepted():
    assert _die_errs(dict(DIE, hold_ff_margin_ps=25)) == []
    assert F.family_margin("hbm", dict(DIE, hold_ff_margin_ps=25)) == 25.0


def test_die_key_range():
    assert any("hold_ff_margin_ps" in e for e in _die_errs(dict(DIE, hold_ff_margin_ps=400)))
    assert any("hold_ff_margin_ps" in e for e in _die_errs(dict(DIE, hold_ff_margin_ps=-1)))


def test_type_key_declared():
    tp = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert tp["hold_ff_margin_ps"] == {"type": "number", "minimum": 0, "maximum": 100}
    errs = []
    S._check(30, tp["hold_ff_margin_ps"], "$.t.hold_ff_margin_ps", errs)
    assert errs == []
