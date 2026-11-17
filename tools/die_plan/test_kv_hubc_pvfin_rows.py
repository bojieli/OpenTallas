import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import kv_hubc_pvfin_rows as R


def plan(W=1200.0, H=900.0):
    return dict(partition_types={"T": dict(outline_um=[W, H], contents=[dict(inst="pvfin", module="qkd_pvfin")],
                                           hard_cores=[dict(inst="ahub", origin_um=[100, 100], outline_um=[300, 200])])})


PINS = dict(outline_um=[207.36, 194.4])


def test_rows_two_cores_nested_and_clear():
    p = R.rows(plan(), "T", PINS)
    t = p["partition_types"]["T"]; hc = {h["inst"]: h for h in t["hard_cores"]}
    lo, hi = hc["pvfin_lo"], hc["pvfin_hi"]
    assert lo["physical_inst"].endswith("g_sl[0].u_sl") and hi["physical_inst"].endswith("g_sl[1].u_sl")
    assert lo["sub_core_parent"] == "pvfin" and lo["sub_core_leaf_pin"] == "rst_n"
    assert t["contents"][0]["module"] == R.PAIR
    r = lambda h: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + 207.36, h["origin_um"][1] + 194.4)
    assert not R.hit(r(lo), r(hi))
    assert not R.hit(r(lo), (95.68, 95.68, 404.32, 304.32)) and not R.hit(r(hi), (95.68, 95.68, 404.32, 304.32))
    assert all(8.64 <= v for h in (lo, hi) for v in h["origin_um"]) and hi["origin_um"][0] + 207.36 <= 1200 - 8.64


def test_no_site_raises():
    try:
        R.rows(plan(300.0, 250.0), "T", PINS)
    except ValueError as e:
        assert "NO_SITE" in str(e); return
    raise AssertionError("expected NO_SITE")


def test_input_plan_not_mutated():
    p0 = plan(); R.rows(p0, "T", PINS)
    assert len(p0["partition_types"]["T"]["hard_cores"]) == 1
