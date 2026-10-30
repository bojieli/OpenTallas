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
