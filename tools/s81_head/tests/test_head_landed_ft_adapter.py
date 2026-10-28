"""LAND-HEAD-BIND-1: hd_tile 8-FT-port adapter (landed form) on the real s81_head plan + the gen_rtl ftspare binding."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "s81_head"))
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import head_landed_ft_adapter as A  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

PLAN = REPO / "physical/die_plan/s81_head/die_plan.json"


@pytest.fixture(scope="module")
def raw():
    if not PLAN.is_file():
        pytest.skip("s81_head plan not in this checkout")
    return json.loads(PLAN.read_text())


NATIVE_TILE = REPO / "rtl/dsrom_sys/s81_head/ot_s81hd_tile_native.sv"


_RT = {}


def _wrapper(P, monkeypatch):
    # the actual leaf header (only the leaf module's header matters) and ONE reset-wavefront solve for the module
    # (~2 min on the full die; the adapter does not touch the reset tree, so every call gets the same hd_tile tree)
    import reset_tree as RT
    orig = _RT.setdefault("orig", RT.for_type)
    monkeypatch.setattr(gen_rtl, "leaf_headers", lambda t, root: NATIVE_TILE.read_text())
    monkeypatch.setattr(RT, "for_type", lambda plan, tn, *a, **k: _RT[tn] if tn in _RT else _RT.setdefault(tn, orig(plan, tn, *a, **k)))
    plan = S.Plan(P, PLAN)
    return gen_rtl.wrapper(plan, "hd_tile", gen_rtl.bus_epochs(plan), str(REPO))


def test_adapter_binds_all_40_ft_pins_without_ties(raw, monkeypatch):
    P, rep = A.apply(raw, repo=REPO)
    assert not S.validate(P)
    t = P["partition_types"]["hd_tile"]
    assert t["contents"][0]["module"] == "ot_s81hd_tile_native"
    assert rep["ports_bound"] == 40 and rep["spare_outputs"] == 20 and rep["ties"] == 0
    for h in t["hard_cores"]:
        assert "head_core_clockfreeze_release" in h["lef"] and (REPO / h["lef"]).is_file()
        lef = (REPO / h["lef"]).read_text()
        assert "PIN ft_mstrap_i" in lef and "PIN clk\n" not in lef
    text = _wrapper(P, monkeypatch)
    inst = text[text.index("ot_s81hd_tile_native"):]
    for k in range(5):
        for n in A.FTS:
            drv = "rst_n" if n == "rst" else "clk"
            assert re.search(rf"\.hci{k}_{n}_i\({drv}\)", inst)
            assert re.search(rf"\.hci{k}_{n}_o\(ftspare_hci{k}_{n}_o\)", inst)
            assert f"wire ftspare_hci{k}_{n}_o;" in text
    assert not re.search(r"\.\w+\(\s*\d+'[bdh]", inst)          # no constant on any leaf pin


def test_adapter_refuses_twice_and_unknown_leaf(raw):
    P, _ = A.apply(raw, repo=REPO)
    with pytest.raises(A.AdapterError):
        A.apply(P, repo=REPO)
    bad = copy.deepcopy(raw)
    bad["partition_types"]["hd_tile"]["contents"][0]["module"] = "ot_s81hd_tile_x"
    with pytest.raises(A.AdapterError):
        A.apply(bad, repo=REPO)


def test_ftspare_must_be_a_bound_output(raw, monkeypatch):
    P, _ = A.apply(raw, repo=REPO)
    t = P["partition_types"]["hd_tile"]
    m = copy.deepcopy(P)
    m["partition_types"]["hd_tile"]["contents"][0]["bind"]["hci0_ck0_i"] = "ftspare:hci0_ck0_o"
    m["partition_types"]["hd_tile"]["contents"][0]["bind"]["hci0_ck0_o"] = "clk"
    with pytest.raises(gen_rtl.GenError):
        _wrapper(m, monkeypatch)
    m = copy.deepcopy(P)
    m["partition_types"]["hd_tile"]["ft_spare_outputs"][0]["owner"] = ""
    with pytest.raises(gen_rtl.GenError):
        _wrapper(m, monkeypatch)
    m = copy.deepcopy(P)                                         # an unbound FT output is an error (no implicit open)
    del m["partition_types"]["hd_tile"]["contents"][0]["bind"][t["ft_spare_outputs"][0]["port"]]
    with pytest.raises(gen_rtl.GenError):
        _wrapper(m, monkeypatch)


def test_adapter_covers_landing_cohort_clones(raw):
    """DIE-HEAD-3: monitor="region" splits hd_tile into landed-mask cohort clones; every clone gets the same adapter."""
    P0 = copy.deepcopy(raw)
    clone = copy.deepcopy(P0["partition_types"]["hd_tile"]); clone["module"] = "hd_tile__clx"; clone["landing_base_type"] = "hd_tile"
    P0["partition_types"]["hd_tile__clx"] = clone
    moved = [p for p in P0["partitions"] if p["type"] == "hd_tile"][:3]
    for p in moved:
        p["type"] = "hd_tile__clx"
    P, rep = A.apply(P0, signed=None)
    assert rep["types"] == ["hd_tile", "hd_tile__clx"] and rep["ports_bound"] == 80 and rep["spare_outputs"] == 40
    for tn in rep["types"]:
        t = P["partition_types"][tn]
        assert t["contents"][0]["module"] == "ot_s81hd_tile_native" and len(t["ft_spare_outputs"]) == 20
    _, rep1 = A.apply(raw, signed=None)
    assert "types" not in rep1 and rep1["ports_bound"] == 40          # no clones: report form unchanged
