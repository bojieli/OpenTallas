"""DIE-HEAD-71 11-05: head_tile_hop_delta.x_relay (l48uh): the u_x direct-lane relay sites follow BST."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_tile_hop_delta as H  # noqa: E402


def tile():
    rs = {}
    for b in H.XDIRECT:
        rs[H.XKEY.format(512 + b)] = [325.92 + 3 * (b % 16), 337.76]          # BST 2 last stage at the cross
        rs[H.XQKEY.format(b - 256)] = [130 + 4 * (b % 16), 1008 - (b >= 384) * 68]
    rs["u_b.bd_r[0]"] = [354, 440]
    cores = [dict(origin_um=o, outline_um=[319.68, 319.68]) for o in ([17.28, 8.64], [362.88, 8.64], [17.28, 380.16],
                                                                        [371.52, 380.16])]
    cores.append(dict(origin_um=[216, 734.4], outline_um=[285.12, 285.12]))
    return dict(outline_um=[708.48, 1036.8], hard_cores=cores, relay_sites=rs)


def test_bst3_rekeys_cross_and_places_band_and_midpoint():
    T = tile()
    before = copy.deepcopy(T["relay_sites"])
    moved = H.x_relay(T, 3)
    rs = T["relay_sites"]
    assert len(moved) == 3 * len(H.XDIRECT)
    for b in H.XDIRECT:
        cross = before[H.XKEY.format(512 + b)]
        assert rs[H.XKEY.format(1024 + b)] == cross                          # last stage at the old cross site
        assert rs[H.XKEY.format(512 + b)] == [cross[0], H.XBAND[256 if b < 384 else 384]]
        x0, y0 = before[H.XQKEY.format(b - 256)]
        s0 = rs[H.XKEY.format(b)]
        band = rs[H.XKEY.format(512 + b)]
        d0 = abs(s0[0] - x0) + abs(s0[1] - y0)
        d1 = abs(band[0] - s0[0]) + abs(band[1] - s0[1])
        assert abs(d0 - d1) < 0.01                                           # stage 0 halves the x_q -> band L route
    assert rs["u_b.bd_r[0]"] == [354, 440]                                   # other keys untouched


def test_bst2_is_noop():
    T = tile()
    before = copy.deepcopy(T)
    assert H.x_relay(T, 2) == {} and T == before


def test_site_on_core_refused():
    T = tile()
    T["hard_cores"].append(dict(origin_um=[300, 700], outline_um=[100, 30]))   # covers the band
    with pytest.raises(AssertionError, match="hard core"):
        H.x_relay(T, 3)
