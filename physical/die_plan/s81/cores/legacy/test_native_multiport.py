"""Native connected multi-PORT access metal must survive kit placement exactly."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import gen_core_kit_legacy as G

@pytest.mark.parametrize("q,rects,w,h", [
    ({"name":"cfg_v","layer":"M3","x":276.453,"y":394.853}, [["M3",276.444,395.242,276.462,395.28],["M3",276.444,394.445,276.462,395.261]],311.04,395.28),
    ({"name":"rst[0]","layer":"M4","x":387.434,"y":135.516}, [["M4",388.716,135.504,388.8,135.528],["M4",386.104,135.504,388.764,135.528]],388.8,172.8),
])
def test_native_connected_edge_access_preserves_logical_center(q,rects,w,h):
    before=dict(q)
    assert G.native_multiport(q,rects,w,h)==rects
    assert q==before
    t="\n".join(G.native_multiport_tcl(q["name"],rects))
    assert t.count("odb::dbBox_create")==2
    assert "place_pin" not in t
    assert all(f"{v:.6f}" in t for a in rects for v in a[1:])
    disconnected=[a[:] for a in rects]
    disconnected[0][1 if q["layer"]=="M4" else 2] += .1
    assert G.native_multiport(q,disconnected,w,h) is None
    assert G.native_multiport(dict(q,x=q["x"]+.001),rects,w,h) is None
    assert G.native_multiport(q,rects[1:],w,h) is None


@pytest.mark.parametrize("q,rects,w,h", [
    (
        {"name": "cfg[47]", "layer": "M3", "x": 16.137, "y": 0.019},
        [["M3", 16.128, 0.0, 16.146, 0.144], ["M3", 16.128, 0.108, 16.146, 1.723]],
        116.64, 198.72,
    ),
    (
        {"name": "ck", "layer": "M4", "x": 0.042, "y": 12.972},
        [["M4", 0.0, 12.96, 0.192, 12.984], ["M4", 0.156, 12.96, 0.275, 12.984]],
        86.4, 25.92,
    ),
])
def test_native_extended_edge_keeps_nominal_pin_site(q, rects, w, h):
    assert G.native_multiport(q, rects, w, h) == rects
    for axis in ("x", "y"):
        moved = dict(q)
        moved[axis] += .001
        assert G.native_multiport(moved, rects, w, h) is None
