"""CUT-SEGMENTS-1: check_cuts keeps one ERROR per cut line (its worst segment) and lists every other segment over the
limit (WARN cuts_segments + summary over_segments with lanes and the whole line); cut_census.py prints / writes it."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check as CK  # noqa: E402
import cut_census as CC  # noqa: E402
import die_trial as DT  # noqa: E402


class _P:
    """three partitions side by side (x 0-100 / 100-200 / 200-300, y 0-1000), one vertical layer of pitch 1 um:
    100 um x 0.25 share = 25 tracks each; a horizontal cut every 250 um."""
    W, H = 300.0, 1000.0
    budgets = {"cut_step_um": 250.0, "cut_ratio_max": 0.6}
    layer_budget = {"cut_avail": {}, "die_layers": []}
    layers = {"M5": {"dir": "V", "pitch_um": 1.0}}
    die = {}

    def __init__(self, lanes):
        self.parts = {"A": {}, "B": {}, "C": {}}
        self._r = {"A": (0, 0, 100, 1000), "B": (100, 0, 200, 1000), "C": (200, 0, 300, 1000)}
        self.lanes = {lid: {"ports": [lid + "__0"]} for lid, _, _ in lanes}
        self.ports = {lid + "__0": {"width": w} for lid, w, _ in lanes}

    def rect(self, n):
        return self._r[n]

    def ptype(self, n):
        return {}


def _run(monkeypatch, lanes):
    monkeypatch.setattr(CK, "cut_owned_segments", lambda P, geo: {})
    monkeypatch.setattr(CK, "cut_child_ports", lambda P: {})
    monkeypatch.setattr(DT, "die_core_cover", lambda P, L: ([], []))
    monkeypatch.setattr(DT, "ft_band_rects", lambda P: [])
    P = _P(lanes)
    geo = {lid: ([(x, 400.0), (x, 600.0)], None, None) for lid, _, x in lanes}    # cross y = 500 only
    R = CK.Report()
    return CK.check_cuts(P, R, geo), R


LANES = [("a1", 12, 30.0), ("a2", 8, 60.0), ("b1", 18, 150.0), ("c1", 5, 250.0)]   # A 20/25 = 0.8, B 0.72, C 0.2


def test_every_over_segment_listed(monkeypatch):
    out, R = _run(monkeypatch, LANES)
    errs = [i for i in R.items if i["level"] == "ERROR" and i["check"] == "cuts"]
    warns = [i for i in R.items if i["check"] == "cuts_segments"]
    assert [e["part"] for e in errs] == ["A"]                       # the ERROR identity set is unchanged (worst only)
    assert "A segment carries 20 bits on 25 tracks = 0.80 > 0.6" in errs[0]["msg"]
    assert [w["part"] for w in warns] == ["B"] and warns[0]["level"] == "WARN"
    segs = out["over_segments"]
    assert [(s["part"], s["worst_of_cut"], s["at_um"], s["orient"]) for s in segs] == [
        ("A", True, 500.0, "horizontal"), ("B", False, 500.0, "horizontal")]
    a = segs[0]
    assert a["bits"] == 20 and a["tracks"] == 25 and a["need_bits"] == 5 and a["lanes"] == [["a1", 12], ["a2", 8]]
    assert [(d["part"], d["slack_bits"]) for d in a["line"]] == [("A", -5), ("B", -3), ("C", 10)]


def test_no_over_segment(monkeypatch):
    out, R = _run(monkeypatch, [("a1", 10, 30.0), ("b1", 15, 150.0)])
    assert out["over_segments"] == [] and not [i for i in R.items if i["check"] in ("cuts", "cuts_segments")]


def test_census_cli(monkeypatch, tmp_path, capsys):
    seg = {"orient": "horizontal", "at_um": 500.0, "part": "A", "ratio": 0.8, "bits": 20, "tracks": 25, "need_bits": 5,
           "worst_of_cut": True, "lanes": [["a1", 12], ["a2", 8]], "line": []}
    monkeypatch.setattr(CC, "census", lambda raw: ([seg], 0.6))
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    out = tmp_path / "c.json"
    assert CC.main([str(plan), "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == {"cut_ratio_max": 0.6, "over_segments": [seg]}
    txt = capsys.readouterr().out
    assert "CUT horizontal@500 A 0.800 bits 20 tracks 25 need 5 WORST lanes a1:12, a2:8" in txt
    assert "CUT-SEGMENTS 1 over 0.6 on 1 cut lines" in txt
