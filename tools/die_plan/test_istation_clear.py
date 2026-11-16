"""istation_clear (S81-LEAF-T14 11-15, FABLE-CLOSURE-STRATEGY lever 4): an internal_stations register inside a macro box moves to
the nearest free point with the row's worst hop kept <= max(LIMIT, before); counts unchanged; a column run through a core with
no such point is refused, or with --grow gets +1 station on the whole bus."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import istation_clear as IC  # noqa: E402


def run(tmp_path, monkeypatch, rows, boxes, extra=()):
    monkeypatch.setattr(IC.SF, "macro_boxes", lambda t: boxes)
    raw = dict(partition_types={"T": dict(outline_um=[1000.0, 1300.0], internal_stations=rows)})
    p = tmp_path / "p.json"; p.write_text(json.dumps(raw))
    IC.main([str(p), str(tmp_path / "o.json"), str(tmp_path / "l.json"), *extra])
    o = json.loads((tmp_path / "o.json").read_text())
    return o.get("T", {}).get("internal_stations"), json.loads((tmp_path / "l.json").read_text())


def row(regs, frm=(500.0, 40.0), to=(500.0, 760.0), conn="core:a|core:b"):
    return dict(conn=conn, from_um=list(frm), regs_um=regs, to_um=list(to), bits=3)


def test_reg_inside_box_moves_out_and_keeps_count(tmp_path, monkeypatch):
    rows, led = run(tmp_path, monkeypatch, [row([[500.0, 400.0]])], [(480.0, 380.0, 520.0, 420.0)])
    e = rows[0]
    assert len(e["regs_um"]) == 1
    x, y = e["regs_um"][0]
    assert not (480.0 < x < 520.0 and 380.0 < y < 420.0)
    assert max(IC.hops(e)) <= 400 + 1e-6
    assert led[0]["regs"] == 1 and led[0]["bits"] == 3


def test_row_without_reg_inside_is_untouched(tmp_path, monkeypatch):
    rows, led = run(tmp_path, monkeypatch, [row([[500.0, 400.0]])], [(100.0, 100.0, 120.0, 120.0)])
    assert rows is None and led == []


def test_refused_then_grown(tmp_path, monkeypatch):
    # 4 regs on a 1912-um column run (hops 382.5); the third sits in a 38 x 63 core: no free point keeps every hop <= 400
    regs = [[500.0, 382.5 * k] for k in (1, 2, 3, 4)]
    core = [(480.0, 382.5 * 3 - 31.0, 518.0, 382.5 * 3 + 32.0)]
    r = row(regs, to=(500.0, 382.5 * 5))
    rows, led = run(tmp_path, monkeypatch, [dict(r)], core)
    assert rows is None and led[0]["refused"]
    rows, led = run(tmp_path, monkeypatch, [dict(r)], core, ("--grow",))
    e = rows[0]
    assert len(e["regs_um"]) == 5 and max(IC.hops(e)) <= 400
    assert not any(core[0][0] < x < core[0][2] and core[0][1] < y < core[0][3] for x, y in e["regs_um"])
