"""RRD corner perimeter path (tools/s81_dv/ctrl_corner.tcl): geometry only, plain tclsh, no OpenROAD."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TCL = Path(__file__).resolve().parent / 'ctrl_corner.tcl'
# cap24 controller body (dbu) and the failing 600-um branch from coord-rep600-s81 (10-22): the rrd pin on the east
# face (centre 96 dbu inside the body) drives a sink 1 um above the north face, 474 um away.
BOX = '12407616 1406592 12796416 1730592'
pytestmark = pytest.mark.skipif(shutil.which('tclsh') is None, reason='tclsh not installed')


def path(a, z, box=BOX, margin=8000):
    script = f'source {{{TCL}}}\nputs [s81_cc_path {{{a}}} {{{z}}} {{{box}}} {margin}]\n'
    with tempfile.NamedTemporaryFile('w', suffix='.tcl') as f:  # a script file: tclsh exits non-zero on error
        f.write(script)
        f.flush()
        r = subprocess.run(['tclsh', f.name], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def legs(text):
    pts = [tuple(float(v) for v in p.split()) for p in text.strip('{}').split('} {')]
    return pts


def test_edge_pin_driver_escapes_through_its_own_face():
    rc, out = path('12796320.0 1412604.0', '12641674.0 1731645.0')
    assert rc == 0, out
    pts = legs(out)
    # starts margin outside the east face at the pin's y, never re-enters the body, ends at the sink
    assert pts[0] == (12804416.0, 1412604.0)
    assert pts[-1] == (12641674.0, 1731645.0)
    x0, y0, x1, y1 = (float(v) for v in BOX.split())
    for (px, py), (qx, qy) in zip(pts, pts[1:]):
        assert px == qx or py == qy
        assert len({(px, py), (qx, qy)}) == 2  # no zero-length leg (it would cost a buffer)
        inside_x = min(px, qx) < x1 and max(px, qx) > x0
        inside_y = min(py, qy) < y1 and max(py, qy) > y0
        assert not (inside_x and inside_y and x0 < px < x1 and y0 < py < y1)


def test_outside_endpoints_are_unchanged():
    # a 160-um branch: both endpoints outside the body -> the original four candidates, the same choice
    rc, out = path('12810000 1500000', '12500000 1750000')
    assert rc == 0, out
    # (byte-identical to ctrl_corner.tcl @528fc3c9f for the same call)
    assert out == '{12810000 1500000} {12804416 1500000} {12804416 1750000} {12500000 1750000}'
    rc, out = path('12300000 1500000', '12500000 1400000')
    assert out == '{12300000 1500000} {12399616 1500000} {12399616 1400000} {12500000 1400000}'


def test_endpoint_deep_inside_the_body_is_still_an_error():
    rc, out = path('12600000 1500000', '12641674.0 1731645.0')
    assert rc != 0 and 'S81_RRD_ENDPOINT_INSIDE_BODY' in out
