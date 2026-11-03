"""DIE-HBM-60: hub_repack.remap_pins keeps every scaled edge pin on its original track phase (check.py on_track)."""
import hub_repack as HR


def _on(c, pitch, off):
    k = (c - off) / pitch
    return abs(k - round(k)) < 1e-4


def test_scaled_edge_pins_stay_on_tracks():
    W, H, H2 = 250.56, 449.28, 414.72
    pins = [dict(name="w%d" % i, layer="M4", x=0.0, y=round(0.024 + 0.048 * (5 * i + 3), 3)) for i in range(400)]
    pins += [dict(name="n%d" % i, layer="M5", x=round(0.024 + 0.048 * (7 * i + 1), 3), y=H) for i in range(100)]
    out = HR.remap_pins(pins, (W, H), (W, H2))
    ws = [p["y"] for p in out if p["name"].startswith("w")]
    assert all(_on(y, 0.048, 0.024) for y in ws)
    assert all(b - a >= 0.192 - 1e-6 for a, b in zip(ws, ws[1:]))
    assert max(ws) < H2
    assert all(_on(p["x"], 0.048, 0.024) and abs(p["y"] - H2) < 1e-6 for p in out if p["name"].startswith("n"))


def test_unscaled_phase_kept_for_m6():
    pins = [dict(name="a", layer="M6", x=0.0, y=96.032), dict(name="b", layer="M6", x=0.0, y=192.032)]
    out = HR.remap_pins(pins, (100.0, 300.0), (100.0, 291.36))
    assert all(_on(p["y"], 0.064, 0.032) for p in out)
