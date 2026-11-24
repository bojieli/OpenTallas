from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "mem_compiler"))

import rom_seam_gate as sg  # noqa: E402
import rom_viamap_gds as vg  # noqa: E402

DBU = 4000  # per um, 0.25 nm


def _box(layer, x0, y0, x1, y1):
    return (vg.rec(vg.BOUNDARY, 0) + vg.rec(vg.LAYER, 2, vg.i2(layer)) + vg.rec(vg.DATATYPE, 2, vg.i2(0))
            + vg.rec(vg.XY, 3, vg.i4(x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)) + vg.rec(vg.ENDEL, 0))


def _sref(name, x, y):
    return (vg.rec(vg.SREF, 0) + vg.rec(vg.SNAME, 6, name.encode()) + vg.rec(vg.XY, 3, vg.i4(x, y))
            + vg.rec(vg.ENDEL, 0))


def _str(name, body):
    return vg.rec(vg.BGNSTR, 2, vg.i2(*([0] * 12))) + vg.rec(vg.STRNAME, 6, name.encode()) + body + vg.rec(vg.ENDSTR, 0)


def nm(v):
    return int(round(v * DBU / 1000))


def _gds(path: Path, gcut=True, band_gate_y0=420.0):
    """Array: short gate x=0 ends y=310, long gate x=54 ends y=364 (contact), VIA1 marker.
    Band cell above: gates at x=0/54 from band_gate_y0, GCUT across the seam."""
    arr = (_box(7, nm(0), nm(0), nm(20), nm(310)) + _box(7, nm(54), nm(0), nm(74), nm(364))
           + _box(21, nm(55), nm(340), nm(73), nm(358)))
    band = _box(7, nm(0), nm(band_gate_y0), nm(20), nm(700)) + _box(7, nm(54), nm(band_gate_y0), nm(74), nm(700))
    if gcut:
        band += _box(10, nm(-30), nm(band_gate_y0 - 22), nm(104), nm(band_gate_y0 + 22))
    top = _sref("arr", 0, 0) + _sref("band", 0, 0)
    path.write_bytes(vg.lib_header(DBU, "t") + _str("arr", arr) + _str("band", band) + _str("top", top)
                     + vg.rec(vg.ENDLIB, 0))


def _run(tmp_path, src, name="out.gds"):
    out = tmp_path / name
    rep = tmp_path / (name + ".json")
    rc = sg.fix(argparse.Namespace(inp=str(src), out=str(out), array_cell="arr", top=None,
                                   min_end_space_nm=100.0, report=str(rep)))
    return rc, out, (json.loads(rep.read_text()) if rep.exists() else None)


def _gates(path):
    _, cells = sg.parse(path)
    return sorted(r for _, r in cells["arr"]["gate"])


def test_long_end_extended_into_gcut_short_kept(tmp_path):
    src = tmp_path / "in.gds"
    _gds(src)
    rc, out, rep = _run(tmp_path, src)
    assert rc == 0 and rep["verdict"] == "PASS"
    assert rep["extended_gates"] == 1 and rep["residual_short_seams"] == 0
    assert rep["unchanged_records_identical"] is True
    assert _gates(out) == [(0, 0, nm(20), nm(310)), (nm(54), 0, nm(74), nm(420))]
    # VIA1 and every other record unchanged
    _, a = sg.parse(src)
    _, b = sg.parse(out)
    assert a["band"] == b["band"]


def test_idempotent(tmp_path):
    src = tmp_path / "in.gds"
    _gds(src)
    _, out, _ = _run(tmp_path, src)
    rc, out2, rep = _run(tmp_path, out, "out2.gds")
    assert rc == 0 and rep["extended_gates"] == 0
    assert out2.read_bytes() == out.read_bytes()


def test_refuses_without_gcut(tmp_path):
    src = tmp_path / "in.gds"
    _gds(src, gcut=False)
    rc, out, rep = _run(tmp_path, src)
    assert rc == 2 and not out.exists()


def test_wide_gap_untouched(tmp_path):
    src = tmp_path / "in.gds"
    _gds(src, band_gate_y0=480.0)  # long end gap 116 nm >= 100
    rc, out, rep = _run(tmp_path, src)
    assert rc == 0 and rep["extended_gates"] == 0
    assert out.read_bytes() == src.read_bytes()


def test_residual_before_and_after(tmp_path):
    src = tmp_path / "in.gds"
    _gds(src)
    assert sg.residual(src, "arr")["short_seams"] == 1
    _, out, _ = _run(tmp_path, src)
    assert sg.residual(out, "arr")["short_seams"] == 0
