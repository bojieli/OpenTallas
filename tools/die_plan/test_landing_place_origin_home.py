"""KV-TYPES-3 11-07: optional clock.landing_origin_rect_um (FIRM home of the START origin)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP  # noqa: E402


class _P:
    def __init__(self, extra=None, copy=False):
        ck = {"landing_contract": {"bands": {}, "pins": [], "collector_root_node": None, "collector_tree": None,
                                   "collector_local_sources": [], "collector_children": []}}
        ck.update(extra or {})
        t = {"outline_um": [1900.0, 1100.0], "clock": ck}
        if copy:
            t["landing_relay_start_copy"] = True
        self.types = {"t": t}


def test_absent_key_is_byte_identical():
    base = LP.tcl(_P(), "t")
    assert "origin-home" not in base
    assert LP._origin_home_groups(_P().types["t"]) == []


def test_rect_emits_one_firm_origin_group():
    out = LP.tcl(_P({"landing_origin_rect_um": [180, 4.32, 230, 48]}), "t")
    assert "{u_cland_origin {180.00000 4.32000 230.00000 48.00000} origin-home}" in out
    assert out.count("origin-home") == 1


def test_relay_start_copy_names_the_rx_origin():
    g = LP._origin_home_groups(_P({"landing_origin_rect_um": [1, 1, 9, 9]}, copy=True).types["t"])
    assert g == [("u_cland_rstart_rx", [1, 1, 9, 9], "origin-home")]


@pytest.mark.parametrize("rect", [[10, 10, 5, 20], [0, 0, 1901, 5], [0, 0, 5], [0, 0, float("nan"), 5], [0, 0, "5", 5]])
def test_bad_rect_fails_closed(rect):
    with pytest.raises(ValueError):
        LP.tcl(_P({"landing_origin_rect_um": rect}), "t")


def test_conflict_with_reader_origin_fails_closed():
    extra = {"landing_origin_rect_um": [1, 1, 9, 9],
             "landing_reader_start": {"depth": 1, "branches": {}, "origin_rect_um": [1, 1, 9, 9]}}
    with pytest.raises(ValueError):
        LP._origin_home_groups(_P(extra).types["t"])


def test_schema_accepts_key():
    import schema as S
    props = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert props["landing_origin_rect_um"]["minItems"] == 4
