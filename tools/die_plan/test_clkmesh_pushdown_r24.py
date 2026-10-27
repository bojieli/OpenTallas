"""CLOCK-KV-R24: 12.2a1 pushdown cells in apply_clkmesh_sites (declared exception) + kv_r24/canon_pushdown."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_clkmesh_sites as A  # noqa: E402
import die_clock_mesh as DCM  # noqa: E402
import schema as S  # noqa: E402
from kv_r24 import canon_pushdown as C  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
W = DCM.cell_width(dict(lib=DCM.BUF))


def _plan(tmp, orient2="MY"):
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["hard_cores"] = [dict(inst="hc", module="m", origin_um=[100.0, 100.0],
                                                      outline_um=[200.0, 200.0], orient="R0", note="t",
                                                      track_offset_um=[0.0, 0.0], pins_file="cores/m.json")]
    next(x for x in p["partitions"] if x["name"] == "pm2")["orient"] = orient2
    p["clock"]["mesh"] = dict(nx=1, ny=1, m=1, rep_um=450.0, ndr="4w", pitch_um=[1.0, 1.0])
    f = tmp / "plan.json"
    f.write_text(json.dumps(p))
    return f, S.Plan(p)


def _build(tmp, P, rows=None):
    """one pushdown driver group per mid instance at core-frame ideal (150.0, 150.12); die placement as the mesh
    build does it (die row ABOVE the die ideal y, group centred on the die ideal x)."""
    cells, pd = {}, []
    for part in ("pm1", "pm2"):
        core = P.types["mid"]["hard_cores"][0]
        X, Y = DCM.core_frame(P, part, core, (150.0, 150.12), inverse=True)
        nm = f"d_{part}"
        for k in range(2):
            cells[f"{nm}_{k}"] = dict(x=round(X - W + k * W, 4), y=round(Y if rows is None else rows, 4), kind="drv")
        pd.append(dict(role="mesh_driver", name=nm, xy=[X, Y], ideal=[X, Y], core=f"{part}/hc"))
    win = []
    for r in pd:
        cs = [cells[r["name"] + f"_{k}"] for k in range(2)]
        win.append([min(c["x"] for c in cs) - 0.054, min(c["y"] for c in cs) - 1e-3,
                    max(c["x"] for c in cs) + W + 0.054, max(c["y"] for c in cs) + 0.27 + 1e-3, r["core"]])
    d = tmp / "b"
    d.mkdir(exist_ok=True)
    (d / "mesh.json").write_text(json.dumps(dict(meta=dict(nx=1, ny=1, m=1, rep_um=450.0, ndr="4w", pitch_um=[1.0, 1.0]),
                                                 pushdown=pd, island_windows=win)))
    (d / "place.json").write_text(json.dumps(cells))
    return d


def _run(args, capsys):
    sys.argv = ["x"] + [str(a) for a in args]
    rc = A.main()
    out = capsys.readouterr().out
    return rc, out


def test_mirrored_instance_needs_canonical_body(tmp_path, capsys):
    f, P = _plan(tmp_path, orient2="MX")
    d = _build(tmp_path, P)
    rc, out = _run([f, d], capsys)
    assert rc == 1 and "core_islands" in out and "2 patterns" in out      # MX instance body = core row below
    o = tmp_path / "c"
    assert C.main([str(f), str(d), str(o)]) == 0
    capsys.readouterr()
    rc, out = _run([f, o, "--write", "--delta-id", "D-T"], capsys)
    assert rc == 0, out
    p = json.loads(f.read_text())
    ci = p["clock"]["mesh"]["core_islands"]["m"]
    assert ci["instances"] == 2 and len(ci["rects_um"]) == 2
    assert ci["rects_um"][0][1] == 150.12 and ci["rects_um"][0][3] == 150.39   # canonical: core row above the point
    # no partition placement hole inside the hard core; schema accepts the record
    for r in p["partition_types"]["mid"].get("clock", {}).get("die_islands_um", []):
        assert not (r[0] < 300 and 100 < r[2] and r[1] < 300 and 100 < r[3])
    assert not [e for e in S.validate_structure(p) if "core_islands" in e]


def test_undeclared_cell_on_core_still_fails(tmp_path, capsys):
    f, P = _plan(tmp_path, orient2="R0")
    d = _build(tmp_path, P)
    m = json.loads((d / "mesh.json").read_text())
    m["island_windows"] = []
    (d / "mesh.json").write_text(json.dumps(m))
    rc, out = _run([f, d], capsys)
    assert rc == 1 and "OVERLAPS [('mid'" in out and '"pushdown_cells": 0' in out


def test_minus():
    assert A.minus((0, 0, 10, 10), (20, 20, 30, 30)) == [(0, 0, 10, 10)]
    parts = A.minus((0, 0, 10, 10), (2, 2, 8, 8))
    assert len(parts) == 4 and abs(sum((r[2] - r[0]) * (r[3] - r[1]) for r in parts) - 64) < 1e-9
    assert A.minus((2, 2, 8, 8), (0, 0, 10, 10)) == []
