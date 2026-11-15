"""istation_respace (S81-LEAF-PLAN 11-15): a pad row with a long end hop is re-spaced at equal arc length (0 cycles),
and grows a stage only when the row is longer than (n+1) x limit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import istation_respace as IR  # noqa: E402


def run(tmp_path, monkeypatch, regs, to):
    monkeypatch.setattr(IR.SF, "macro_boxes", lambda t: [])
    monkeypatch.setattr(IR.SF, "off_macro", lambda boxes, xy: tuple(xy))
    monkeypatch.setattr(IR, "reprice", lambda old, raw: {})
    raw = dict(partition_types={"T": dict(internal_stations=[dict(conn="core:a|core:b", from_um=[0.0, 0.0],
                                                                   regs_um=regs, to_um=to)])})
    p = tmp_path / "p.json"; p.write_text(json.dumps(raw))
    IR.main([str(p), str(tmp_path / "o.json"), str(tmp_path / "l.json")])
    return json.loads((tmp_path / "o.json").read_text())["partition_types"]["T"]["internal_stations"][0]


def test_equal_arc_respace_keeps_count(tmp_path, monkeypatch):
    e = run(tmp_path, monkeypatch, [[100.0, 0.0]], [700.0, 0.0])
    assert e["regs_um"] == [[350.0, 0.0]] and max(IR.hops(e)) <= 400


def test_adds_a_stage_when_too_long(tmp_path, monkeypatch):
    e = run(tmp_path, monkeypatch, [[100.0, 0.0]], [900.0, 0.0])
    assert len(e["regs_um"]) == 2 and max(IR.hops(e)) <= 400
