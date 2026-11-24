"""pytest: TAPKEY-SITE tap_site re-key by site (renumber after a re-solve), diff report, gen_phys stamp hook."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tap_site as TS  # noqa: E402

OLD = {"clk_t0": (10.0, 10.0), "clk_t1": (500.0, 10.0), "clk_t2": (900.0, 10.0)}
# re-solve: a new tap inserted at the left renumbers every later tap, clk_t2's old site is gone
NEW = {"clk_t0": (5.0, 5.0), "clk_t1": (10.0, 12.0), "clk_t2": (500.0, 10.0), "clk_t3": (700.0, 10.0)}


def _plan():
    return {"clock": {"tap_offset": {"per_port_ps": {"A": {"clk_t0": {"TT": 1}, "clk_t1": {"TT": 2}, "clk_t2": {"TT": 3},
                                                            "clk_c0": {"TT": 9}}}},
                      "tap_window": {"per_port_ps": {"A": {"clk_t1": 40}}}},
            "partition_types": {"A": {"clock": {"tap_sites_um": {p: list(xy) for p, xy in OLD.items()},
                                                "tap_pin_heights_um": {"clk_t1": 2.0},
                                                "tap_group": {"re": "(x)", "fixed_taps": {"g0": "clk_t0", "g2": "clk_t2"}}}},
                                "B": {"clock": {}}}}


def test_site_map_renumber_one_to_one():
    m, uns = TS.site_map(OLD, NEW)
    assert m == {"clk_t0": "clk_t1", "clk_t1": "clk_t2"} and uns == ["clk_t2"]


def test_rekey_renumber_moves_rows_with_their_site():
    raw = _plan()
    r = TS.rekey_type(raw, "A", NEW)
    off = raw["clock"]["tap_offset"]["per_port_ps"]["A"]
    assert off == {"clk_t1": {"TT": 1}, "clk_t2": {"TT": 2}, "clk_c0": {"TT": 9}}     # t2 row unsited -> dropped; core kept
    assert raw["clock"]["tap_window"]["per_port_ps"]["A"] == {"clk_t2": 40}
    tck = raw["partition_types"]["A"]["clock"]
    assert tck["tap_pin_heights_um"] == {"clk_t2": 2.0}
    assert tck["tap_group"]["fixed_taps"] == {"g0": "clk_t1"}
    assert tck["tap_sites_um"]["clk_t3"] == [700.0, 10.0] and r["renamed"] == 2 and r["unsited"] == ["clk_t2"]
    assert r["tables"]["clock.tap_offset.per_port_ps"] == {"renamed": 2, "dropped": 1}


def test_rekey_is_idempotent_and_unchanged_grid_is_noop():
    raw = _plan()
    TS.rekey_type(raw, "A", NEW)
    once = copy.deepcopy(raw)
    TS.rekey_type(raw, "A", NEW)
    assert raw == once
    raw2 = _plan()
    r = TS.rekey_type(raw2, "A", OLD)
    assert r["renamed"] == 0 and not r["unsited"] and raw2["clock"]["tap_offset"] == _plan()["clock"]["tap_offset"]


def test_unstamped_type_untouched_and_swap_does_not_collide():
    raw = _plan()
    assert TS.rekey_type(raw, "B", NEW) is None
    swap = {"clk_t0": (500.0, 10.0), "clk_t1": (10.0, 10.0), "clk_t2": (900.0, 10.0)}
    TS.rekey_type(raw, "A", swap)
    off = raw["clock"]["tap_offset"]["per_port_ps"]["A"]
    assert off["clk_t1"] == {"TT": 1} and off["clk_t0"] == {"TT": 2} and off["clk_t2"] == {"TT": 3}


def test_check_and_diff_report_moved_names_with_tables():
    raw = _plan()
    moved, n = TS.check_type(raw, "A", NEW)
    assert n == 3 and [(p, q) for p, q, _ in moved] == [("clk_t0", "clk_t1"), ("clk_t1", "clk_t2"), ("clk_t2", None)]
    d = TS.diff_type(raw, raw, "A", NEW, OLD)
    names = {q: set(t) for q, _d, t in d["moved"]}
    assert set(names) == {"clk_t0", "clk_t1", "clk_t2"}
    assert names["clk_t1"] == {"clock.tap_offset.per_port_ps", "clock.tap_window.per_port_ps", "tap_pin_heights_um"}
    assert names["clk_t2"] == {"clock.tap_offset.per_port_ps", "tap_group.fixed_taps"}
    assert d["new"] == 1 and d["gone"] == 0 and d["common"] == 3


def test_rekey_plan_skips_unevaluable_grid():
    raw = _plan()
    logs = []
    reps = TS.rekey_plan(raw, "p.json", P=object(), log=logs.append)       # schema.tap_grid raises on a bogus Plan
    assert reps == [] and "not evaluable" in logs[0] and raw == _plan()


def test_adv_tapkey_site_never_raises():
    import adv_tapkey_site as A
    assert A.findings(None, "p")[0].startswith("WARN ADV-TAPKEY-SITE")


def test_stamp_from_baseline_then_rekey_renumber(monkeypatch):
    import types as _ty
    grids = {"base": [("clk", 0.0, 0.0)] + [(n, x, y) for n, (x, y) in OLD.items()],
             "cur": [("clk", 0.0, 0.0)] + [(n, x, y) for n, (x, y) in NEW.items()]}

    class _P:
        def __init__(self, raw, path):
            self.tag = raw["tag"]
    monkeypatch.setitem(sys.modules, "schema", _ty.SimpleNamespace(Plan=_P, tap_grid=lambda P, tn: grids[P.tag]))
    raw = _plan()
    del raw["partition_types"]["A"]["clock"]["tap_sites_um"]           # c8 case: rows never stamped
    raw["tag"] = "cur"
    base = {"tag": "base", "partition_types": {"A": {"clock": {}}}}
    assert TS.stamp_from_baseline(raw, base, "b.json") == 1
    assert raw["partition_types"]["A"]["clock"]["tap_sites_um"]["clk_t2"] == [900.0, 10.0]
    reps = TS.rekey_plan(raw, "p.json", log=lambda m: None)
    assert reps[0]["renamed"] == 2 and reps[0]["unsited"] == ["clk_t2"]
    assert raw["clock"]["tap_offset"]["per_port_ps"]["A"] == {"clk_t1": {"TT": 1}, "clk_t2": {"TT": 2}, "clk_c0": {"TT": 9}}
