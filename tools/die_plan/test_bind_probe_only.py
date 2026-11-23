"""PROBE-ONLY-1123: OT_BIND_ONLY_TYPES type selection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import pytest  # noqa: E402

BY = {"svc_a__t1": ["p1"], "svc_a__t1__v1": ["p2"], "slw_b": ["p3"], "cut_x": ["p4"]}
TY = {"svc_a__t1": {}, "svc_a__t1__v1": {"split_of": "svc_a__t1"}, "slw_b": {}, "cut_x": {"split_of": "base_x"}}


def test_unset_is_full_bind(monkeypatch):
    monkeypatch.delenv("OT_BIND_ONLY_TYPES", raising=False)
    assert bind.only_types_select(BY, TY) is None


def test_selects_name_variants_and_split_base(monkeypatch):
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "svc_a__t1, base_x")
    assert bind.only_types_select(BY, TY) == {"svc_a__t1", "svc_a__t1__v1", "cut_x"}
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "slw_*")
    assert bind.only_types_select(BY, TY) == {"slw_b"}


def test_unknown_name_refuses(monkeypatch):
    monkeypatch.setenv("OT_BIND_ONLY_TYPES", "slw_b,nope")
    with pytest.raises(bind.BindError):
        bind.only_types_select(BY, TY)
