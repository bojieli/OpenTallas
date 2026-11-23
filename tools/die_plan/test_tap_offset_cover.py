"""TAPOFF-ALL 11-23 (FABLE-UNC-KV, DIE-FIX-LEDGER x10): all-mode coverage census + fill of plan clock.tap_offset.per_port_ps."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402
import tap_offset_cover as C  # noqa: E402


def _raw(sites, listed, tn="src", added=()):
    """tiny plan whose type tn has a per_port_ps row for `listed`; schema.tap_grid is monkeypatched to `sites`."""
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_offset"] = dict(per_port_ps={tn: {p: {"TT": 0.1 * x, "FF": 0.08 * x, "tol": 10.0}
                                                        for p, (x, _y) in sites.items() if p in listed}}, source="test", proof="x")
    raw["partition_types"][tn].setdefault("clock", {})["added_taps"] = [dict(name=p, xy=list(sites[p])) for p in added]
    return raw


SITES = {"clk": (0.0, 0.0), "clk_t1": (100.0, 0.0), "clk_t2": (200.0, 0.0), "clk_t3": (300.0, 0.0), "clk_t4": (400.0, 0.0),
         "clk_t5": (150.0, 10.0), "clk_t6": (250.0, 10.0)}


def _grid(monkeypatch, sites=SITES, fail=None):
    def tap_grid(P, tn):
        if fail:
            raise ValueError(fail)
        return [(n, x, y) for n, (x, y) in sites.items()]
    monkeypatch.setattr(schema, "tap_grid", tap_grid)
    monkeypatch.setattr(schema, "core_taps", lambda P, tn: [("clk_c0", 5.0, 5.0, {})])


def test_census_passes_when_every_grid_port_is_listed(monkeypatch):
    _grid(monkeypatch)
    rows = C.census(_raw(SITES, set(SITES)))
    assert [r["status"] for r in rows] == ["OK"] and C.census_rc(rows) == 0
    assert rows[0]["core_missing"] == 1            # a core tap without a row is listed, it does not fail the census


def test_census_fails_on_an_added_tap_without_a_row_in_any_mode(monkeypatch):
    _grid(monkeypatch)
    for mode in ("density", "grid+explicit", "explicit", None):
        raw = _raw(SITES, set(SITES) - {"clk_t5", "clk_t6"}, added=("clk_t5", "clk_t6"))
        if mode:
            raw["partition_types"]["src"]["clock"]["tap_mode"] = mode
        r = C.census(raw)[0]
        assert (r["status"], r["missing"], r["sample"]) == ("MISSING", 2, "clk_t5,clk_t6"), mode
        assert C.census_rc([r]) == 1


def test_census_reports_a_type_it_cannot_evaluate_and_fails(monkeypatch):
    _grid(monkeypatch, fail="src: added tap clk_t5 violates outline/halo/tap spacing")
    raw = _raw(SITES, set(SITES) - {"clk_t6"}, added=("clk_t5", "clk_t6"))
    r = C.census(raw)[0]
    assert r["status"] == "UNEVALUATED" and "violates" in r["why"]
    assert r["missing"] == 1 and r["sample"] == "clk_t6"        # the added taps are still compared by name (lower bound)
    assert C.census_rc([r]) == 1
    raw = _raw(SITES, set(SITES), added=("clk_t5", "clk_t6"))   # nothing missing by name: still not a pass
    assert C.census_rc(C.census(raw)) == 1


def test_fill_estimates_from_neighbours_with_a_measured_tolerance(monkeypatch):
    _grid(monkeypatch)
    raw = _raw(SITES, set(SITES) - {"clk_t5", "clk_t6"}, added=("clk_t5", "clk_t6"))
    raw["clock"]["tap_offset"]["per_port_ps"]["src"]["gone"] = {"TT": 1.0, "FF": 1.0, "tol": 10.0}
    rep = C.fill(raw)
    tab = raw["clock"]["tap_offset"]["per_port_ps"]["src"]
    assert rep[0]["added"] == 2 and rep[0]["stale_removed"] == 1 and "gone" not in tab
    assert 10.0 < tab["clk_t5"]["TT"] < 20.0 and 20.0 < tab["clk_t6"]["TT"] < 30.0      # between the taps around them (offset = 0.1 x)
    assert tab["clk_t5"]["tol"] >= 10.0 and tab["clk_t5"]["tol"] >= float(rep[0]["loo_p95"])
    assert "tap_offset_cover fill: 2" in raw["clock"]["tap_offset"]["source"]
    assert C.census_rc(C.census(raw)) == 0 and schema.validate(raw) == []
    assert C.fill(raw) == []                         # idempotent


def test_fill_refuses_a_type_with_too_few_listed_taps(monkeypatch):
    _grid(monkeypatch)
    raw = _raw(SITES, {"clk", "clk_t1"})
    rep = C.fill(raw)
    assert rep[0]["status"].startswith("SKIP") and rep[0]["added"] == 0
    assert set(raw["clock"]["tap_offset"]["per_port_ps"]["src"]) == {"clk", "clk_t1"}


def test_fill_of_an_unevaluated_type_uses_its_listed_added_taps_only(monkeypatch):
    _grid(monkeypatch, fail="tap solver error")
    add = ("clk_t1", "clk_t2", "clk_t3", "clk_t4", "clk_t5", "clk_t6")
    raw = _raw(SITES, set(SITES) - {"clk_t6"}, added=add)
    rep = C.fill(raw)
    assert rep[0]["added"] == 1 and "unevaluated" in rep[0]["status"]
    assert "clk_t6" in raw["clock"]["tap_offset"]["per_port_ps"]["src"]
    assert C.census_rc(C.census(raw)) == 1           # still unevaluated: the census keeps failing until the grid solves


def test_cli_rc(tmp_path, monkeypatch):
    _grid(monkeypatch)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(_raw(SITES, set(SITES) - {"clk_t6"}, added=("clk_t6",))))
    assert C.main(["census", str(p), "--out", str(tmp_path / "c.tsv")]) == 1
    assert C.main(["fill", str(p), str(tmp_path / "out.json"), "--report", str(tmp_path / "f.tsv")]) == 0
    assert C.main(["census", str(tmp_path / "out.json")]) == 0
    assert "clk_t6" in (tmp_path / "f.tsv").read_text() or "ESTIMATED" in (tmp_path / "f.tsv").read_text()


def _wraw(listed, added=()):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_window"] = dict(window_ps=80.0, related_pair_ps=80.0, note="flat W",
                                      per_port_ps={"src": {p: 10 + int(SITES[p][0] // 100) for p in SITES if p in listed}})
    raw["partition_types"]["src"].setdefault("clock", {})["added_taps"] = [dict(name=p, xy=list(SITES[p])) for p in added]
    return raw


def test_window_form_census_and_fill(monkeypatch):
    """TAPWIN-ALL (S81 x9): a port missing from a clock.tap_window.per_port_ps row falls back to the flat W_t."""
    _grid(monkeypatch)
    raw = _wraw(set(SITES) - {"clk_t5", "clk_t6"}, added=("clk_t5", "clk_t6"))
    r = C.census(raw)[0]
    assert (r["form"], r["status"], r["missing"]) == ("window", "MISSING", 2) and C.census_rc([r]) == 1
    assert C.census(raw, form="offset") == []
    rep = C.fill(raw)
    tab = raw["clock"]["tap_window"]["per_port_ps"]["src"]
    assert rep[0]["status"] == "NEIGHBOUR-MAX" and rep[0]["added"] == 2
    assert tab["clk_t5"] == 12 and tab["clk_t6"] == 13          # the largest window of the 3 nearest listed taps, no interpolation
    assert "tap_offset_cover fill: 2" in raw["clock"]["tap_window"]["note"]
    assert C.census_rc(C.census(raw)) == 0 and schema.validate(raw) == []


def test_offsets_row_wins_over_a_window_row_of_the_same_type(monkeypatch):
    _grid(monkeypatch)
    raw = _raw(SITES, set(SITES))
    raw["clock"]["tap_window"] = dict(window_ps=80.0, per_port_ps={"src": {"clk": 12}})
    assert [(r["form"], r["status"]) for r in C.census(raw)] == [("offset", "OK")]
