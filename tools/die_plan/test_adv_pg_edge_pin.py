"""ADV-PG-EDGE-PIN (COORD 11-24): hard-core edge pins on parent PG stripe columns, cores without pg_halo_um."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(**kw):
    """an st_a-like region core at (8.64, 8.64): M5 pins on its S edge every 0.144 um from x 0.072"""
    pins = [{"name": f"s[{i}]", "layer": "M5", "xy": [0.072 + 0.144 * i, 0.0]} for i in range(30)]
    pins += [{"name": "mid", "layer": "M5", "xy": [2.16 - 8.64 + 8.64, 10.0]},           # not an edge pin
             {"name": "e0", "layer": "M6", "xy": [20.0, 2.16 + 4.32 - 8.64 + 8.64]},     # E edge, on an M6 row
             {"name": "m4", "layer": "M4", "xy": [2.16, 0.0]}]                            # not a PG stripe layer
    return dict(dict(inst="u_r0", module="st_a_region", origin_um=[8.64, 8.64], outline_um=[20.0, 20.0], pins=pins), **kw)


def plan(**kw):
    return {"partition_types": {"sle_st_a": {"outline_um": [100.0, 100.0], "hard_cores": [core(**kw)]}}}


def test_edge_pins_on_stripe_columns_are_counted():
    n, hits = G.pg_edge_pins(core(), Path("."))
    # M5 columns at 2.16 + 4.32k in the type frame -> core-frame x = 2.16 + 4.32k - 8.64 (mod 4.32) = 2.16, 6.48 ...
    xs = sorted({h[2] for h in hits if h[1] == "M5"})
    assert all(min((x - 2.16) % 4.32, 4.32 - (x - 2.16) % 4.32) < 0.156 + 0.072 for x in xs)
    assert n == 31 and len(xs) >= 2 and any(h[0] == "e0" and h[1] == "M6" for h in hits)
    assert not any(h[0] in ("mid", "m4") for h in hits)
    out = G.pg_edge_pin(plan(), "p.json")
    assert out[0].startswith("WARN ADV-PG-EDGE-PIN sle_st_a: core u_r0 (st_a_region): ") and "no pg_halo_um" in out[0]
    assert out[-1].startswith(f"LIST ADV-PG-EDGE-PIN {len(hits)} edge pin(s) on 1 hard core(s)")


def test_pg_halo_and_orient_and_pins_file(tmp_path):
    assert G.pg_edge_pin(plan(pg_halo_um=1.296), "p.json") == []
    (tmp_path / "pins.json").write_text(json.dumps({"pins": [{"bus": "d", "bit": 0, "layer": "M5", "x": 20.0 - 2.16 + 8.64 - 8.64 - 0.0, "y": 20.0}]}))
    hc = dict(inst="u_c", module="m", origin_um=[0.0, 0.0], outline_um=[20.0, 20.0], orient="MY", pins_file="pins.json")
    n, hits = G.pg_edge_pins(hc, tmp_path)                       # MY: x -> 20 - x = 2.16 (a stripe centre), N edge
    assert n == 1 and hits and hits[0][0] == "d[0]" and hits[0][2] == 2.16


def test_registered_in_plan_advisory():
    assert ("PG-EDGE-PIN", "adv_pg_edge_pin") in PA.CHECKS
    import adv_pg_edge_pin
    assert adv_pg_edge_pin.findings is G.pg_edge_pin
