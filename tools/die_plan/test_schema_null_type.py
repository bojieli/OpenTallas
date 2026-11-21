"""schema._check: JSON type "null" (die_plan.schema.json clock.zl_lockup.<T>.guard is ["string", "null"];
station_rule.apply --seams writes guard None, and gen.py latency / check.py validation raised KeyError 'null')."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402


def test_null_type():
    s = {"type": "object", "properties": {"guard": {"type": ["string", "null"]}}}
    for v in (None, "x"):
        errs = []
        S._check({"guard": v}, s, "$", errs)
        assert errs == []
    errs = []
    S._check({"guard": 3}, s, "$", errs)
    assert errs and "expected" in errs[0]
    errs = []
    S._check(None, {"type": "null"}, "$", errs)
    assert errs == []
