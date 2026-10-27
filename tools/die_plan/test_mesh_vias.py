"""Fail-closed die clock mesh continuity (COORD PATH-S81-PD12 ruling A, 2026-10-27): a mesh without an M8-M9 VIA89 at
every strap crossing is not one connected net and must fail G0 (check.py --clock-build), the mesh sign-off STA and the
clock report.  Runs under pytest or directly (python3 test_mesh_vias.py)."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import die_clock_mesh as DCM  # noqa: E402
import die_sta_related as DSR  # noqa: E402


def mesh(vias=None, regions=None, spans=None):
    M = dict(xs=[0.0, 100.0, 200.0], ys=[0.0, 50.0], taps=[], drivers={}, meta=dict(ndr="4w"))
    if vias is not None:
        M["meta"]["mesh_vias"] = vias
    if regions is not None:
        M["meta"]["regions"] = regions
    if spans is not None:
        M["strap_spans"] = spans
    return M


def write(d, M, logs=None):
    d = Path(d)
    (d / "mesh.json").write_text(json.dumps(M))
    for c, txt in (logs or {}).items():
        (d / f"combo_{c}.log").write_text(txt)
    return d


def test_crossings_regionless_and_clipped():
    assert DCM.mesh_crossings(mesh(), DCM.mesh_regions(mesh())[0]) == 6
    g = dict(k=0, i0=0, i1=3, j0=0, j1=2)
    # M8 row 1 clipped to x <= 100 (macro hole): crossings (0,1),(1,1) remain; column 2 removed entirely
    sp = {"H:0:0": [0.0, 200.0], "H:1:0": [0.0, 100.0], "V:0:0": [0.0, 50.0], "V:1:0": [0.0, 50.0], "V:2:0": None}
    assert DCM.mesh_crossings(mesh(regions=[g], spans=sp), g) == 4


def test_no_vias_fails_closed():
    f = DCM.mesh_via_findings(mesh())
    assert len(f) == 1 and "no M8-M9 vias" in f[0] and "6 strap crossings" in f[0]
    assert DCM.mesh_connected(mesh()) == {None: False}


def test_short_count_and_routed_db():
    assert DCM.mesh_via_findings(mesh(vias={"None": 5}))[0].startswith("ck_mesh: 5 emitted")
    assert DCM.mesh_via_findings(mesh(vias={"None": 6})) == []
    with tempfile.TemporaryDirectory() as t:
        d = write(t, mesh(vias={"None": 6}), {"TT": "OT_MESH_VIAS ck_mesh 6\n", "FF": "no via line\n"})
        f = DCM.mesh_via_findings(json.loads((d / "mesh.json").read_text()), d)
        assert len(f) == 1 and "routed DB has 0" in f[0], f     # FF's DB carried no vias: fail closed
        (d / "combo_FF.log").write_text("OT_MESH_VIAS ck_mesh 6\n")
        assert DCM.mesh_via_findings(json.loads((d / "mesh.json").read_text()), d) == []
        (d / "combo_FF.log").write_text("OT_MESH_VIAS ck_mesh 2\n")
        f = DCM.mesh_via_findings(json.loads((d / "mesh.json").read_text()), d)
        assert len(f) == 1 and "routed DB has 2" in f[0]
        (d / "combo_TT.log").write_text("x\n")
        (d / "combo_FF.log").write_text("x\n")
        f = DCM.mesh_via_findings(json.loads((d / "mesh.json").read_text()), d)
        assert len(f) == 1 and "routed DB via count missing" in f[0]
        assert DCM.mesh_connected(json.loads((d / "mesh.json").read_text()), d) == {None: False}


def test_regions_each_checked():
    rg = [dict(k=0, i0=0, i1=2, j0=0, j1=2), dict(k=1, i0=2, i1=3, j0=0, j1=2)]
    f = DCM.mesh_via_findings(mesh(vias={"0": 4, "1": 1}, regions=rg))
    assert f == ["ck_mesh_r1: 1 emitted M8-M9 vias < 2 strap crossings"]
    assert DCM.mesh_connected(mesh(vias={"0": 4, "1": 1}, regions=rg)) == {0: True, 1: False}


def test_no_straps_no_mesh():
    assert DCM.mesh_via_findings(dict(xs=[], ys=[], meta={})) == []


def test_combo_defaults_to_vias(monkeypatch=None):
    orig = DCM.cmd_combo
    DCM.cmd_combo = lambda a: a
    try:
        assert DCM.main(["combo", "d", "--kit", "k"]).mesh_vias is True
        assert DCM.main(["combo", "d", "--kit", "k", "--mesh-vias"]).mesh_vias is True
        assert DCM.main(["combo", "d", "--kit", "k", "--no-mesh-vias"]).mesh_vias is False
    finally:
        DCM.cmd_combo = orig


def test_check_clock_build_is_g0_error():
    with tempfile.TemporaryDirectory() as t:
        d = write(t, mesh())
        for compl in (False, True):
            R = check.Report(compl)
            out = check.check_clock_mesh(R, [str(d)])
            assert out[0]["continuous"] is False
            assert [i["level"] for i in R.items] == ["ERROR"] and R.items[0]["check"] == "clock_mesh"
        write(t, mesh(vias={"None": 6}), {"TT": "OT_MESH_VIAS ck_mesh 6\n"})
        R = check.Report(True)
        assert check.check_clock_mesh(R, [str(d)])[0]["continuous"] is True and R.items == []
        R = check.Report(False)
        check.check_clock_mesh(R, [str(Path(t) / "missing")])
        assert R.errors() and "no mesh.json" in R.errors()[0]["msg"]


def test_mesh_signoff_refuses_unconnected_mesh():
    with tempfile.TemporaryDirectory() as t:
        d = write(t, mesh())
        (d / "mesh_TT.json").write_text(json.dumps(dict(stubs={})))
        so = d / "so.json"
        so.write_text(json.dumps(dict(corner="TT", loads=[], arr=[], grad_vec_ps=[])))
        try:
            DSR.mesh_signoff(d, {}, {}, "TT", so)
        except SystemExit as e:
            assert "not continuous" in str(e)
        else:
            raise AssertionError("mesh sign-off accepted a mesh without crossing vias")


if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_") and callable(v):
            v()
            n += 1
            print("PASS", k)
    print(f"{n} tests PASS")


def test_meshvia_gate_ignores_generator_log_but_keeps_missing_corner_failure(tmp_path):
    import die_clock_mesh as D
    (tmp_path / "combo_TT.log").write_text("OT_MESH_VIAS ck_mesh 6\n")
    (tmp_path / "combo_gen.log").write_text("combo written; no routed DB\n")
    (tmp_path / "combo_report.log").write_text("diagnostic generator output\n")
    assert D.routed_mesh_vias(tmp_path)[0] == {"ck_mesh": 6}
    (tmp_path / "combo_FF.log").write_text("failed before via report\n")
    assert D.routed_mesh_vias(tmp_path)[0] == {"ck_mesh": 0}
