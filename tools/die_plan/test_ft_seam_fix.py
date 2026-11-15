"""ft_seam_fix (S81-LEAF-PLAN 11-14): a lane hop from the LAST station of a crossed slot over the seam is found, the
last station is re-sited toward the out face when that clears it, and a station is appended (+1 on the crossing
lanes' latency rows) when it does not.  Geometry stand-in: one R0 partition, lane src -> slot stations -> dst."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_seam_fix as FS  # noqa: E402


def plan(regs, dst=(1400.0, 100.0), src=(-10.0, 100.0), lanes=("ln0",)):
    t = dict(outline_um=[1000.0, 400.0],
             ft_slots=[dict(name="ft0", in_face="W", out_face="E", stations=len(regs), regs_um=[list(r) for r in regs],
                            in_window_um=[90.0, 110.0], out_window_um=[90.0, 110.0], width=4)])
    raw = dict(partition_types={"T": t},
               latency=dict(lanes={ln: dict(stations=len(regs), cycles=len(regs) + 2, natural=len(regs) + 2)
                                   for ln in lanes}))
    P = SimpleNamespace(raw=raw, types=raw["partition_types"], parts={"p0": dict(type="T")},
                        lanes={ln: {} for ln in lanes})
    P.slot = lambda part, sn: t["ft_slots"][0]
    P.lane_crossings = lambda lid: [("p0", "ft0", None, None)]
    P._src, P._dst = src, dst
    return P, raw, t


def fake_hops(P, lid):
    s = P.types["T"]["ft_slots"][0]
    pts = [P._src] + [tuple(r) for r in s["regs_um"]] + [P._dst]
    return [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])]


def setup(monkeypatch):
    monkeypatch.setattr(FS, "lane_hops", fake_hops)


def test_finds_only_the_last_station_seam_hop(monkeypatch):
    setup(monkeypatch)
    P, raw, t = plan([(0.0, 100.0), (390.0, 100.0), (780.0, 100.0)])      # last -> dst 620 um
    f = FS.seam_hops(P, 400.0)
    assert [(x[0], x[2], x[3], x[5]) for x in f] == [("ln0", "T", "ft0", "last->seam")]
    P2, _, _ = plan([(0.0, 100.0), (390.0, 100.0), (780.0, 100.0)], dst=(1100.0, 100.0))
    assert FS.seam_hops(P2, 400.0) == []


def test_resite_moves_last_station_toward_out_face(monkeypatch):
    setup(monkeypatch)
    P, raw, t = plan([(0.0, 100.0), (390.0, 100.0), (700.0, 100.0)], dst=(1150.0, 100.0))   # 450 > 400
    rec = {}
    assert FS.fix_slot(P, raw, "T", "ft0", 400.0, False, rec)
    s = t["ft_slots"][0]
    assert rec["action"] == "resite" and s["stations"] == 3
    hops = fake_hops(P, "ln0")
    assert max(hops) <= 400.0 and s["regs_um"][-1][0] > 700.0
    assert raw["latency"]["lanes"]["ln0"]["cycles"] == 5          # no latency change


def test_add_station_when_resite_cannot_clear(monkeypatch):
    setup(monkeypatch)
    P, raw, t = plan([(0.0, 100.0), (390.0, 100.0), (780.0, 100.0)], dst=(1300.0, 100.0))   # out face at 1000
    rec = {}
    assert not FS.fix_slot(P, raw, "T", "ft0", 400.0, False, rec) and "re-site" in rec["why"]
    rec = {}
    assert FS.fix_slot(P, raw, "T", "ft0", 400.0, True, rec)
    s = t["ft_slots"][0]
    assert rec["action"] == "add" and s["stations"] == len(s["regs_um"]) >= 4
    assert max(fake_hops(P, "ln0")) <= 400.0
    r = raw["latency"]["lanes"]["ln0"]
    assert r["stations"] == s["stations"] and r["cycles"] == s["stations"] + 2


def test_failed_add_restores_the_slot(monkeypatch):
    setup(monkeypatch)
    P, raw, t = plan([(0.0, 100.0), (390.0, 100.0), (780.0, 100.0)], dst=(5000.0, 100.0))   # unreachable
    before = [list(r) for r in t["ft_slots"][0]["regs_um"]]
    rec = {}
    assert not FS.fix_slot(P, raw, "T", "ft0", 400.0, True, rec)
    s = t["ft_slots"][0]
    assert s["stations"] == 3 and s["regs_um"] == before and raw["latency"]["lanes"]["ln0"]["cycles"] == 5


def test_off_macro_moves_a_centre_out_of_the_box():
    boxes = [(100.0, 100.0, 200.0, 300.0)]
    assert FS.off_macro(boxes, (50.0, 50.0)) == [50.0, 50.0]
    q = FS.off_macro(boxes, (105.0, 200.0))          # nearest edge is x0: out by 5 + 2 um gap
    assert q == [98.0, 200.0]
    assert FS.off_macro(boxes, (150.0, 296.0)) == [150.0, 302.0]
