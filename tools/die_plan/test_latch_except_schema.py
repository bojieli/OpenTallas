"""clock.core_input_lockup accepts latch_except (port or port[bit]) and latch_except_hb4 (bit -> 1..8 HB4); other keys stay refused."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _errs(cfg):
    raw = copy.deepcopy(PAIR)
    raw.setdefault("clock", {})["core_input_lockup"] = cfg
    r = schema.validate_structure(raw)
    return [str(e) for e in (r if isinstance(r, (list, tuple)) else [r] if r else [])]


BASE = {"modules": {"m": ["tap"]}, "types": ["fb"], "pipe": 1}


def test_bit_level_rows_validate():
    for extra in ({"latch_except": {"m": ["tap[0]"]}},
                  {"latch_except": {"m": ["tap[0]"]}, "latch_except_hb4": {"m": {"tap[0]": 3}}}):
        assert not [e for e in _errs(dict(BASE, **extra)) if "latch_except" in e], extra


def test_unknown_key_and_bad_pad_are_refused():
    assert [e for e in _errs(dict(BASE, latch_exceptt={})) if "latch_exceptt" in e]
    assert [e for e in _errs(dict(BASE, latch_except_hb4={"m": {"tap[0]": 0}})) if "latch_except_hb4" in e or "minimum" in e]
