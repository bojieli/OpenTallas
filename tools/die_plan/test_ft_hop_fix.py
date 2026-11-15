"""ft_hop_fix (S81-LEAF-PLAN 11-15): an in-slot hop gets a station in its middle (off macros), and --grow-gaps grows the
lower partition's N face into an empty seam gap with the face-site registers following the face."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_hop_fix as HF  # noqa: E402


def no_macros(monkeypatch):
    monkeypatch.setattr(HF.SF, "macro_boxes", lambda t: [])
    monkeypatch.setattr(HF.SF, "off_macro", lambda boxes, xy: tuple(xy))


def test_insert_station_splits_the_hop(monkeypatch):
    no_macros(monkeypatch)
    s = dict(name="ft0", stations=3, regs_um=[[0.0, 0.0], [0.0, 800.0], [0.0, 1000.0]])
    assert HF.insert_station({}, s, 0)
    assert s["stations"] == 4 and s["regs_um"][1] == [0.0, 400.0]


def test_insert_station_falls_back_off_a_macro(monkeypatch):
    monkeypatch.setattr(HF.SF, "macro_boxes", lambda t: [])
    monkeypatch.setattr(HF.SF, "off_macro", lambda boxes, xy: None if abs(xy[1] - 400.0) < 1 else tuple(xy))
    s = dict(name="ft0", stations=2, regs_um=[[0.0, 0.0], [0.0, 800.0]])
    assert HF.insert_station({}, s, 0)
    assert abs(s["regs_um"][1][1] - 320.0) < 1e-6                      # second fraction (.4)


def test_grow_gaps_abuts_and_moves_face_registers(monkeypatch):
    lo = dict(outline_um=[100.0, 200.0], ft_slots=[dict(name="ft0", in_face="N", out_face="S", stations=2,
                                                        regs_um=[[50.0, 200.0], [50.0, 20.0]])])
    hi = dict(outline_um=[100.0, 200.0], ft_slots=[])
    raw = dict(partition_types={"LO": lo, "HI": hi},
               die=dict(channels=[dict(name="band", between=["a", "b"]), dict(name="other", between=["a", "c"])]))
    P = SimpleNamespace(types=raw["partition_types"],
                        parts={"a": dict(type="LO", origin_um=[0.0, 0.0], orient="R0"),
                               "b": dict(type="HI", origin_um=[0.0, 500.0], orient="R0")})
    monkeypatch.setattr(HF.SF, "lane_labels", lambda P, lid: ["src", ("b", "ft9", 0), ("a", "ft0", 0), "dst"])
    out = HF.grow_gaps(P, raw, [("ln", 450.0, ("b", "ft9"), "seam", 0)])
    assert out == [("LO", "N", 300.0, "a", "b")]
    assert lo["outline_um"] == [100.0, 500.0]
    assert lo["ft_slots"][0]["regs_um"] == [[50.0, 500.0], [50.0, 20.0]]
    assert [c["name"] for c in raw["die"]["channels"]] == ["other"]
