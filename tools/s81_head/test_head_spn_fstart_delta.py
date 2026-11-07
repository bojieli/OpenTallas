"""DIE-HEAD-77 11-06: head_spn_fstart_delta (l48uj): closeout partition take + FSTART per-face leaves + kit transform check."""
import copy, os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_spn_fstart_delta as D

LEAF = {"name": "fstart_face_ad_o", "raw": "rst_rl_14", "xy_um": [500.62, 12.06], "consumers": ["u_cland_fstart_ad_o"]}


def plans():
    T = {"module": "m", "outline_um": [1, 2], "buses": [], "clock": {"landing_local_resets": [{"name": "geo_0"}]},
         "reset": {"a": 1}}
    base = {"partition_types": {"hd_spn": copy.deepcopy(T), "hd_spn_end": copy.deepcopy(T), "hd_tile": {"x": 1}}}
    clo = copy.deepcopy(base)
    for t in D.TYPES:
        clo["partition_types"][t]["reset"] = {"a": 2}
        clo["partition_types"][t]["internal_stations"] = [1]
    clo["partition_types"]["hd_tile"] = {"x": 2}
    return base, clo


def test_takes_only_the_two_types():
    base, clo = plans()
    diffs = D.take_types(base, clo)
    assert diffs == {"hd_spn": ["internal_stations", "reset"], "hd_spn_end": ["internal_stations", "reset"]}
    assert base["partition_types"]["hd_tile"] == {"x": 1}
    assert base["partition_types"]["hd_spn"]["reset"] == {"a": 2}


def test_refuses_pin_or_outline_change():
    base, clo = plans()
    clo["partition_types"]["hd_spn"]["outline_um"] = [1, 3]
    with pytest.raises(SystemExit):
        D.take_types(base, clo)


def test_adds_leaves_once():
    base, _ = plans()
    assert D.add_leaves(base, [LEAF]) == 1
    names = [e["name"] for e in base["partition_types"]["hd_spn"]["clock"]["landing_local_resets"]]
    assert names == ["geo_0", "fstart_face_ad_o"]
    with pytest.raises(SystemExit):
        D.add_leaves(base, [LEAF])


def test_changed_lines_ignore_position():
    a = "x\ny\nz\n"; b = "x\nY\nz\n"
    assert D.changed("p\n" + a, "p\n" + b) == D.changed(a, b) == ["-y", "+Y"]
