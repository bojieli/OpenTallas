import copy, pathlib, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import rebind_head_native_release_fwd as R


def base():
    return {"pads": [{"name": "pma_rx", "dir": "in", "width": 2}], "clock": {"landing_contract": {"pins": []}, "reserved_sites_um": []}}


def test_physical_delta_refused_by_default():
    a, b = base(), base()
    b["pads"][0].update(layer="M7", sites_um=[[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="physical-only"):
        R.fwd_only_delta(copy.deepcopy(a), copy.deepcopy(b))


def test_physical_delta_allowed_with_flag():
    a, b = base(), base()
    b["pads"][0].update(layer="M7", sites_um=[[1, 2], [3, 4]])
    b["clock"]["reserved_sites_um"] = [{"rect_um": [0, 0, 1, 1]}]
    R.fwd_only_delta(a, b, allow_physical=True)


def test_other_change_still_refused():
    a, b = base(), base()
    b["pads"][0]["width"] = 3
    with pytest.raises(ValueError):
        R.fwd_only_delta(a, b, allow_physical=True)


def test_core_origin_and_regions_physical_only():
    a, b = base(), base()
    a["hard_cores"] = [{"inst": "u_chn", "origin_um": [1, 2]}]
    b["hard_cores"] = [{"inst": "u_chn", "origin_um": [1, 9]}]
    b["place_regions"] = [{"name": "r"}]
    with pytest.raises(ValueError, match="physical-only"):
        R.fwd_only_delta(copy.deepcopy(a), copy.deepcopy(b))
    R.fwd_only_delta(a, b, allow_physical=True)
