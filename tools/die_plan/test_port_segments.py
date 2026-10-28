"""KV-PLAN-DELTA-9: multi-window hop ports (`segments`, COORD 10-27 20:04 ruling (ii))."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

LAY = {L["name"]: L for L in S.ASAP7_LAYERS}


def _port(**kw):
    p = dict(id="p", src=dict(part="a", bus="x"), dst=dict(part="b", bus="y_i"), width=1118, kind="data", face="W",
             layers=["M4", "M6"], window_um=[11217.0, 11448.0], order="lsb_low")
    p.update(kw)
    return p


def _old_pin_positions(port, layers):
    """pre-D9 pin_positions (reference copy) for the byte-identity check of plain ports."""
    import math
    lo, hi = sorted(port["window_um"])
    names = port["layers"]
    w = S.port_pins_count(port)
    nl = len(names)
    rev = port.get("order", "lsb_low") == "lsb_high"
    out = []
    for li, ln in enumerate(names):
        L = layers[ln]
        p, off = L["pitch_um"], L["offset_um"]
        bits = list(range(li, w, nl))
        n = len(bits)
        k0 = math.ceil((lo - off) / p - 1e-9)
        k1 = math.floor((hi - off) / p + 1e-9)
        A = [k for k in range(k0, k1 + 1) if not S.pg_blocked(ln, off + k * p)]
        idx = S.spread(A, n, (lo - off) / p, (hi - off) / p)
        for j, b in enumerate(bits):
            slot = (n - 1 - j) if rev else j
            out.append((b, ln, round(off + A[idx[slot]] * p, 6)))
    out.sort()
    return out


@pytest.mark.parametrize("width,order", [(1118, "lsb_low"), (559, "lsb_high"), (7, "lsb_low"), (1, "lsb_low")])
def test_plain_port_unchanged(width, order):
    p = _port(width=width, order=order)
    assert S.pin_positions(p, LAY) == _old_pin_positions(p, LAY)


def _seg_port():
    segs = [dict(pins=560, window_um=[11218.08, 11288.48]), dict(pins=559, window_um=[11639.18, 11709.5])]
    return _port(segments=segs, window_um=[11218.08, 11709.5])


def test_segments_cover_and_stay_in_windows():
    p = _seg_port()
    pins = S.pin_positions(p, LAY)
    assert [b for b, _, _ in pins] == list(range(1119))          # every pin once, epoch pin included
    for b, ln, c in pins:
        lo, hi = (11218.08, 11288.48) if b < 560 else (11639.18, 11709.5)
        assert lo - 1e-6 <= c <= hi + 1e-6
        assert ln == ("M4" if b % 2 == 0 else "M6")               # global bit parity kept (F1 face class)
    # one segment equals the plain placement of its own pins on its window
    seg1 = [x for x in pins if x[0] >= 560]
    ref = S._window_pins(p, LAY, [11639.18, 11709.5], list(range(560, 1119)))
    assert seg1 == ref


def test_segment_density_le_8_per_um():
    p = _seg_port()
    for b0, b1, w in S.port_segments(p):
        assert (b1 - b0) / (w[1] - w[0]) <= 8.0 + 1e-9


def test_mirror_segments_match_type_table():
    """an E/W-mirrored N/S instance (lsb_high + mirrored windows) puts every bit at the mirrored coordinate."""
    W = 864.0                     # die lattice multiple (8.64): tracks are mirror-symmetric
    segs = [dict(pins=300, window_um=[100.0, 140.0]), dict(pins=259, window_um=[400.0, 440.0])]
    a = _port(face="S", layers=["M5", "M7"], width=558, segments=segs, window_um=[100.0, 440.0])
    msegs = [dict(pins=s["pins"], window_um=[W - s["window_um"][1], W - s["window_um"][0]]) for s in segs]
    b = _port(face="S", layers=["M5", "M7"], width=558, segments=msegs, window_um=[W - 440.0, W - 100.0],
              order="lsb_high")
    pa = {k: c for k, _, c in S.pin_positions(a, LAY)}
    pb = {k: c for k, _, c in S.pin_positions(b, LAY)}
    assert pa.keys() == pb.keys()
    assert all(abs((W - pa[k]) - pb[k]) < 1e-6 for k in pa)


def test_segments_must_cover_port():
    p = _seg_port()
    p["segments"][1]["pins"] = 500
    with pytest.raises(ValueError, match="segments carry"):
        S.port_segments(p)


def test_plain_port_one_segment():
    p = _port()
    assert S.port_segments(p) == [(0, 1119, [11217.0, 11448.0])]


def test_schema_accepts_segments():
    errs = []
    S._check(_seg_port(), S.SCHEMA["properties"]["ports"]["items"], "ports[0]", errs)
    assert errs == []
    bad = _seg_port()
    bad["segments"][0]["extra"] = 1
    errs = []
    S._check(bad, S.SCHEMA["properties"]["ports"]["items"], "ports[0]", errs)
    assert errs
